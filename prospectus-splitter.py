import os
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
import json
from multiprocessing import Pool, cpu_count

# Set up base directory and input/output structure
input_dir = 'example_input'
output_dir = 'example_output'

# Ensure the output directory exists
os.makedirs(output_dir, exist_ok=True)

# Define keywords for each extraction type
keywords_dict = {
    "cover_underwriter": [
        ["keterangan tentang penjaminan emisi efek"],
        ["susunan dan jumlah porsi penjaminan"]
    ],
    "balance_sheet": [
        ["laporan posisi keuangan", "cash and cash equivalent", "catatan/"],
        ["laporan posisi keuangan", "cash", "total assets", "catatan/"],
        ["laporan posisi keuangan", "piutang", "jumlah aset", "catatan"],
        ["laporan posisi keuangan", "piutang", "total aset", "catatan"],
        ["consolidated statement", "piutang", "total aset", "catatan/"],
        ["piutang", "total aset", "notes"],
        ["piutang", "jumlah aset", "notes"]
    ],
    "cash_flow": [
        ["laporan arus kas", "arus kas dari", "aktivitas operasi", "catatan/"],
        ["laporan arus kas", "arus kas dari", "catatan/"],
        ["laporan arus kas", "arus kas dari", "catatan"],
        ["arus kas dari", "aktivitas operasi", "catatan"]
    ],
    "income_statement": [
        ["laporan laba rugi", "penjualan", "pokok penjualan", "catatan/"],
        ["laporan laba rugi", "revenues", "beban pokok", "catatan/"],
        ["laporan laba rugi", "revenue", "beban pokok", "catatan/"],
        ["laporan laba rugi", "penjualan", "beban pokok", "catatan"],
        ["laporan laba rugi", "pendapatan", "beban pokok", "catatan"],
        ["laporan laba rugi", "income", "catatan/"],
        ["laporan laba rugi", "pendapatan", "catatan/"],
        ["laporan laba rugi", "pendapatan usaha", "catatan"],
        ["laporan laba rugi", "pendapatan", "catatan"],
        ["penjualan", "beban pokok", "catatan"]
    ]
}

# Stop and anti-keywords
stop_keywords = {
    "balance_sheet": [["laba per saham", "jumlah ekuitas", "total ekuitas"]],
    "cash_flow": [["kas dan setara kas", "kas dan bank", "kas dan setara"]],
    "income_statement": [
        ["per saham", "total comprehensive", "laba komprehensif", "laba bersih per"]
    ]
}

# Anti-keywords to exclude pages with irrelevant content
anti_keywords = {
    "cover_underwriter": [],
    "balance_sheet": [],
    "cash_flow": [],
    "income_statement": [
        ["laporan perubahan ekuitas", "laporan arus kas"]
    ]
}

# Helper function to create output file paths
def create_output_path(file_name, extraction_type):
    folder_name = os.path.join(output_dir, os.path.splitext(file_name)[0])
    os.makedirs(folder_name, exist_ok=True)
    return os.path.join(folder_name, f"{os.path.splitext(file_name)[0]}_{extraction_type}.pdf")

# Function to handle JSON data creation and updating
def update_json(file_name, extraction_type, page_start, page_end):
    json_path = os.path.join(output_dir, os.path.splitext(file_name)[0], f"{os.path.splitext(file_name)[0]}.json")
    
    # Load existing JSON data if available, otherwise create a new structure
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            json_data = json.load(json_file)
    else:
        json_data = {}

    # Add or update the specific extraction type with page info
    if extraction_type == "cover_underwriter":
        # For cover_underwriter, use "cover" and "underwriter" instead of "page_start" and "page_end"
        json_data[extraction_type] = {
            "edited": json_data.get(extraction_type, {}).get("edited", 0),
            "cover": page_start,        # Using page_start as cover page
            "underwriter": page_end     # Using page_end as underwriter page
        }
    else:
        json_data[extraction_type] = {
            "edited": json_data.get(extraction_type, {}).get("edited", 0),
            "page_start": page_start,
            "page_end": page_end
        }

    # Write updated JSON data back to file
    with open(json_path, 'w') as json_file:
        json.dump(json_data, json_file, indent=4)

# Function to check if re-split is needed based on JSON settings and file existence
def should_resplit(file_name, extraction_type):
    json_path = os.path.join(output_dir, os.path.splitext(file_name)[0], f"{os.path.splitext(file_name)[0]}.json")
    output_pdf_path = create_output_path(file_name, extraction_type)

    # Load JSON data if it exists
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            json_data = json.load(json_file)
        section_data = json_data.get(extraction_type, {"edited": 0})
        edited = section_data["edited"]
    else:
        edited = 0

    file_exists = os.path.exists(output_pdf_path)

    # Determine action based on the table logic
    if edited == 0 and file_exists:
        return False  # Skip split
    elif edited == 0 and not file_exists:
        return True   # Regular split
    elif edited == 1:
        return True   # Re-split based on defined pages (no 3-page cap)

# General extraction function with manual editing logic
def extract_pages(file_name, extraction_type):
    if not should_resplit(file_name, extraction_type):
        return f"Skipped {extraction_type}: {file_name} - Edited=0 and File Exists"

    input_pdf_path = os.path.join(input_dir, file_name)
    output_pdf_path = create_output_path(file_name, extraction_type)

    # Load JSON data to check if specific pages are defined (for Edited=1)
    json_path = os.path.join(output_dir, os.path.splitext(file_name)[0], f"{os.path.splitext(file_name)[0]}.json")
    page_range = None
    cover_page_num = None
    underwriter_page_num = None
    if os.path.exists(json_path):
        with open(json_path, 'r') as json_file:
            json_data = json.load(json_file)
            section_data = json_data.get(extraction_type)
            if section_data and section_data["edited"] == 1:
                if extraction_type == "cover_underwriter":
                    cover_page_num = section_data.get("cover", 1) - 1  # Convert to 0-based index
                    underwriter_page_num = section_data.get("underwriter", 1) - 1  # Convert to 0-based index
                else:
                    page_range = range(section_data["page_start"] - 1, section_data["page_end"])

    keywords_sets = keywords_dict[extraction_type]
    stop_kw = stop_keywords.get(extraction_type, [])
    anti_kw = anti_keywords.get(extraction_type, [])

    try:
        matched_keywords = None
        pages_to_extract = []

        with fitz.open(input_pdf_path) as doc:
            total_pages = doc.page_count

            # Special handling for "cover_underwriter"
            if extraction_type == "cover_underwriter":
                reader = PdfReader(input_pdf_path)
                writer = PdfWriter()

                # When Edited=1, extract only the specified pages in JSON
                if cover_page_num is not None and underwriter_page_num is not None:
                    # Validate page numbers
                    if cover_page_num < 0 or cover_page_num >= total_pages:
                        return f"Error: Cover page number {cover_page_num + 1} is out of range for {file_name}"
                    if underwriter_page_num < 0 or underwriter_page_num >= total_pages:
                        return f"Error: Underwriter page number {underwriter_page_num + 1} is out of range for {file_name}"

                    writer.add_page(reader.pages[cover_page_num])
                    writer.add_page(reader.pages[underwriter_page_num])
                    extracted_pages = [cover_page_num, underwriter_page_num]
                    with open(output_pdf_path, 'wb') as out_file:
                        writer.write(out_file)

                    # No JSON update to maintain edited flag as 1
                    return f"Extracted {extraction_type}: {file_name} - Pages {[p + 1 for p in extracted_pages]}"

                # Regular extraction for cover_underwriter (cover and first matching underwriter page)
                # Add the cover page (first page)
                writer.add_page(reader.pages[0])
                extracted_pages = [0]  # Cover page (1-based index: page 1)

                # Search for the first page with underwriter keywords and add it
                for page_num in range(1, total_pages):  # Start from second page
                    page_text = doc.load_page(page_num).get_text().lower()
                    if any(all(keyword in page_text for keyword in keywords) for keywords in keywords_sets):
                        writer.add_page(reader.pages[page_num])
                        extracted_pages.append(page_num)
                        break  # Stop after finding the first underwriter page

                # Write to output PDF
                with open(output_pdf_path, 'wb') as out_file:
                    writer.write(out_file)

                # Update JSON with 1-based page numbers (edited flag remains unchanged)
                update_json(file_name, extraction_type, extracted_pages[0] + 1, extracted_pages[-1] + 1)
                return f"Extracted {extraction_type}: {file_name} - Pages {[p + 1 for p in extracted_pages]}"
            else:
                # Standard processing for other types (balance_sheet, cash_flow, income_statement)
                reader = PdfReader(input_pdf_path)
                writer = PdfWriter()
                
                # Extract specified pages if Edited=1
                if page_range:
                    for page_num in page_range:
                        writer.add_page(reader.pages[page_num])
                    extracted_pages = list(page_range)
                    with open(output_pdf_path, 'wb') as out_file:
                        writer.write(out_file)

                    # No JSON update to maintain edited flag as 1
                    return f"Extracted {extraction_type}: {file_name} - Pages {[p + 1 for p in extracted_pages]}"

                # Standard extraction for Edited=0 (3-page limit, stop/anti-keywords)
                midpoint = total_pages // 2
                second_half_start = midpoint
                second_half_end = total_pages

                for keywords in keywords_sets:
                    for page_num in range(second_half_start, second_half_end):
                        page = doc.load_page(page_num)
                        text = page.get_text().lower()

                        if all(keyword in text for keyword in keywords):
                            matched_keywords = keywords
                            pages_to_extract.append(page_num)
                            break

                    if pages_to_extract:
                        break

                # Extract pages if matches found
                if pages_to_extract:
                    page_num = pages_to_extract[0]

                    # Add up to three pages
                    extracted_pages = []
                    for i in range(3):
                        if page_num + i < total_pages:
                            page_text = doc.load_page(page_num + i).get_text().lower()

                            # Skip if anti-keywords are found
                            if any(anti_word in page_text for anti_list in anti_kw for anti_word in anti_list):
                                break

                            writer.add_page(reader.pages[page_num + i])
                            extracted_pages.append(page_num + i)

                            # Stop extraction if stop keyword is found
                            if any(stop_word in page_text for stop_list in stop_kw for stop_word in stop_list):
                                break

                    with open(output_pdf_path, 'wb') as out_file:
                        writer.write(out_file)

                    # Update JSON with 1-based page numbers if edited=0
                    update_json(file_name, extraction_type, extracted_pages[0] + 1, extracted_pages[-1] + 1)
                    return f"Extracted {extraction_type}: {file_name} - Pages {[p + 1 for p in extracted_pages]}"
                else:
                    return f"Not Extracted {extraction_type}: {file_name} - No matching pages found"
    except Exception as e:
        return f"Error with {file_name} ({extraction_type}): {e}"

# Process a single file for all extraction types
def process_file(file_name):
    results = []
    for extraction_type in keywords_dict.keys():
        result = extract_pages(file_name, extraction_type)
        results.append(result)
    return results

# Main script execution with multiprocessing
if __name__ == '__main__':
    pdf_files = [file_name for file_name in os.listdir(input_dir) if file_name.lower().endswith('.pdf')]

    with Pool(cpu_count()) as pool:
        all_results = pool.map(process_file, pdf_files)

    # Display all results
    for file_results in all_results:
        for result in file_results:
            print(result)
