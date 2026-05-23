import os
import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from collections import deque, Counter
import subprocess

# === CONFIGURATION ===
domain = "https://www.exampledomain.com"
sitemap_url = "https://www.exampledomain.com/sitemap.xml"
cli_path = r'"C:\Program Files (x86)\Screaming Frog SEO Spider\ScreamingFrogSEOSpiderCli"'
base_folder = r"C:\K-ScreamingFrog"
sf_export_name = "internal_all.csv"
batch_size = 1000

# === HEADERS to bypass 403 ===
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# === Derived Paths ===
safe_domain_name = domain.replace("https://", "").replace("http://", "").replace("/", "_")
domain_folder = os.path.join(base_folder, safe_domain_name)
os.makedirs(domain_folder, exist_ok=True)

internal_csv = os.path.join(domain_folder, sf_export_name)
master_list_path = os.path.join(domain_folder, f"list_{safe_domain_name}.txt")
summary_path = os.path.join(domain_folder, "summary.txt")
robots_txt_path = os.path.join(domain_folder, "robots.txt")
llms_txt_path = os.path.join(domain_folder, "llms.txt")

# === Helpers ===
def split_into_batches(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]

def extract_subdomain(url):
    try:
        parts = urlparse(url).hostname.split('.')
        return '.'.join(parts[:-2]) if len(parts) > 2 else ''
    except:
        return ''

def try_download_file(url, save_path):
    try:
        r = requests.get(url, timeout=10, headers=headers)
        r.raise_for_status()
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(r.text)
        return r.text
    except Exception as e:
        print(f"⚠️ Failed to download {url}: {e}")
        return None

def parse_sitemap(root_sitemap):
    all_urls = set()
    queue = deque([root_sitemap])
    seen = set()

    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        try:
            r = requests.get(current, timeout=10, headers=headers)
            r.raise_for_status()
            tree = ET.fromstring(r.content)

            if tree.tag.endswith("sitemapindex"):
                queue.extend([n.text.strip() for n in tree.findall(".//{*}loc")])
            elif tree.tag.endswith("urlset"):
                all_urls.update(n.text.strip() for n in tree.findall(".//{*}loc"))
        except Exception as e:
            print(f"⚠️ Error parsing sitemap {current}: {e}")
    return sorted(all_urls)

# === Phase 0: Download robots.txt & llms.txt ===
parsed = urlparse(domain)
base_url = f"{parsed.scheme}://{parsed.netloc}"
robots_text = try_download_file(f"{base_url}/robots.txt", robots_txt_path)
llms_text = try_download_file(f"{base_url}/llms.txt", llms_txt_path)

# === Phase 1: Extract URLs from Sitemap ===
print(f"🌐 Extracting URLs from sitemap: {sitemap_url}")
urls = parse_sitemap(sitemap_url)

if not urls:
    print("❌ No URLs found. Aborting.")
    exit(1)

with open(master_list_path, "w", encoding="utf-8") as f:
    for url in urls:
        f.write(url + "\n")
print(f"✅ Master list saved: {master_list_path} ({len(urls)} URLs)")

# === Phase 2: Batch Crawl via Screaming Frog CLI ===
subdomains = []
batch_output_files = []

for idx, batch in enumerate(split_into_batches(urls, batch_size), start=1):
    batch_file = os.path.join(domain_folder, f"batch_{idx}.txt")
    with open(batch_file, "w", encoding="utf-8") as f:
        f.write("\n".join(batch))

    output_csv = os.path.join(domain_folder, f"batch{idx}_internal_all.csv")
    print(f"🚀 Crawling batch {idx} with {len(batch)} URLs...")

    crawl_command = (
        f'{cli_path} --headless --crawl-list "{batch_file}" '
        f'--export-tabs internal:all --export-format csv '
        f'--output-folder "{domain_folder}" --overwrite'
    )

    try:
        subprocess.run(crawl_command, shell=True, check=True)
        time.sleep(2)

        if os.path.exists(internal_csv):
            os.rename(internal_csv, output_csv)
            batch_output_files.append(output_csv)
            print(f"✅ Exported: {output_csv}")
        else:
            print(f"⚠️ No output file found for batch {idx}.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Screaming Frog: {e}")
    finally:
        if os.path.exists(batch_file):
            os.remove(batch_file)
    print("-" * 50)

# === Phase 3: Combine Results ===
if not batch_output_files:
    print("❌ No batch files to combine. Exiting.")
    exit(1)

print("📊 Combining output files...")
dfs = []
for f in batch_output_files:
    try:
        dfs.append(pd.read_csv(f))
    except Exception as e:
        print(f"⚠️ Could not read {f}: {e}")

if not dfs:
    print("❌ All CSV reads failed.")
    exit(1)

combined_df = pd.concat(dfs, ignore_index=True)
excel_path = os.path.join(domain_folder, "full_combined_output.xlsx")
combined_df.to_excel(excel_path, index=False)
print(f"📘 Excel saved: {excel_path}")

# === Phase 4: Summary ===
for row in combined_df.itertuples(index=False):
    try:
        addr = getattr(row, "Address", "")
        sub = extract_subdomain(addr)
        if sub:
            subdomains.append(sub)
    except:
        continue

sub_count = Counter(subdomains)
with open(summary_path, "w", encoding="utf-8") as f:
    f.write(f"🔢 Total URLs (from sitemap): {len(urls)}\n")
    f.write(f"🌐 Unique subdomains found: {len(sub_count)}\n")
    for sub, count in sub_count.items():
        f.write(f"  - {sub}: {count} URLs\n")
    f.write(f"\n🔍 robots.txt found: {'Yes' if robots_text else 'No'}\n")
    f.write(f"🔍 llms.txt found: {'Yes' if llms_text else 'No'}\n")
    f.write(f"🔗 Sitemap source: {sitemap_url}\n")

print(f"📄 Summary saved: {summary_path}")
