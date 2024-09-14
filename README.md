# Goodreads Book Cover Generator and Report

This project automates the generation of book cover images for a Goodreads library and compiles a detailed PDF report. If a cover image isn't available via the ISBN, a colorful placeholder cover is generated.

## Features

- Fetches book cover images from Open Library and Google Books.
- Automatically generates colorful placeholder covers for books without images.
- Generates a detailed reading report as a PDF, including charts, book cover thumbnails, and statistics.
- Handles missing or invalid ISBNs and generates a report for books without covers.

## Prerequisites

- Python 3.x
- The following Python libraries:
  - `pandas`
  - `matplotlib`
  - `seaborn`
  - `fpdf`
  - `Pillow`
  - `requests`

## How to Use

1. Clone the repository:
    ```bash
    git clone https://github.com/your_username/book-cover-generator
    ```

2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Place your `goodreads_library_export.csv` in the root directory of the project.

4. Run the script:
    ```bash
    python generate_report.py
    ```

5. The output will be a PDF report titled `goodreads_professional_report.pdf` and a report for missing covers as `missing_books_report.txt`.

## Example Output

The generated PDF report includes:
- A summary of books read per year.
- A chart showing pages read per year.
- Individual book cover images (fetched from Open Library or Google Books, or generated as colorful placeholders).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
