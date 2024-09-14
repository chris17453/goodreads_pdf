import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os
import re
from urllib.parse import quote
import random

# Directory to save book covers
cover_dir = 'book_covers'
not_found_report = 'missing_books_report.txt'

# Ensure directories exist
if not os.path.exists(cover_dir):
    os.makedirs(cover_dir)

# List to store information about missing covers
missing_books = []

# Function to clean the ISBN (remove extra characters like quotes and equal signs)
def clean_isbn(isbn):
    """Clean the ISBN field from extra quotes and equal signs."""
    if pd.isna(isbn):
        return None
    # Remove leading/trailing quotes and equal signs
    clean_isbn = re.sub(r'[="]', '', str(isbn).strip())
    return clean_isbn if clean_isbn else None

# Function to clean the title by removing anything in parentheses
def clean_title(title):
    """Remove anything inside parentheses from the title."""
    return re.sub(r'\(.*?\)', '', title).strip()

# Function to check if the file exists and is valid (greater than 0 bytes and not 631 bytes)
def is_valid_file(path):
    return os.path.exists(path) and os.path.getsize(path) > 0 and os.path.getsize(path) != 631

# Function to search Open Library for an ISBN using title and author
def get_isbn_from_open_library(title, author):
    """Search Open Library by title and author and return the ISBN if available."""
    base_url = "https://openlibrary.org/search.json"
    params = {
        'title': title,
        'author': author
    }
    
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'docs' in data and len(data['docs']) > 0:
                # Return the first ISBN found in the search results
                for doc in data['docs']:
                    if 'isbn' in doc:
                        return doc['isbn'][0]  # Return the first ISBN in the list
        return None
    except Exception as e:
        print(f"Error fetching ISBN from Open Library: {e}")
        return None


def generate_generic_cover(title, author, pub_date, cover_path):
    """Generate a generic book cover with a colorful background and large, bright fonts (Fedora-compatible)."""
    
    # List of bright colors for the background
    bright_colors = [
        (255, 99, 71),   # Tomato Red
        (135, 206, 250), # Sky Blue
        (255, 165, 0),   # Orange
        (124, 252, 0),   # Lawn Green
        (255, 105, 180), # Hot Pink
        (32, 178, 170),  # Light Sea Green
        (147, 112, 219), # Medium Purple
        (255, 223, 0)    # Gold
    ]
    
    # Pick a random color for the background
    bg_color = random.choice(bright_colors)
    
    # Create the image with the random bright background color
    img = Image.new('RGB', (400, 600), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Set the text content (Title, Author, and Publication Date)
    title_text = f"{title}"
    author_text = f"By: {author}"
    pub_date_text = f"Published: {pub_date}"

    # Try to use a large font available on Fedora, fallback to default if unavailable
    font_path = None
    possible_paths = [
        "/usr/share/fonts/google-droid-sans-fonts/DroidSans-Bold.ttf",  # Droid Sans Bold
        "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",                 # Open Sans Bold
        "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",     # Liberation Sans Bold
    ]

    # Find the first valid font path
    for path in possible_paths:
        if os.path.exists(path):
            font_path = path
            break

    if font_path:
        font = ImageFont.truetype(font_path, 40)  # Large font size
        font_small = ImageFont.truetype(font_path, 30)
    else:
        print("Font not found, using default.")
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Use a bright color for the text (white or black)
    text_color = (255, 255, 255) if bg_color != (255, 223, 0) else (0, 0, 0)  # White text, black if background is gold
    
    # Calculate text bounding box to center it
    title_bbox = draw.textbbox((0, 0), title_text, font=font)
    author_bbox = draw.textbbox((0, 0), author_text, font=font_small)
    pub_date_bbox = draw.textbbox((0, 0), pub_date_text, font=font_small)

    title_width = title_bbox[2] - title_bbox[0]
    author_width = author_bbox[2] - author_bbox[0]
    pub_date_width = pub_date_bbox[2] - pub_date_bbox[0]

    # Centering title, author, and publication date on the image
    draw.text(((400 - title_width) // 2, 150), title_text, fill=text_color, font=font)
    draw.text(((400 - author_width) // 2, 300), author_text, fill=text_color, font=font_small)
    draw.text(((400 - pub_date_width) // 2, 400), pub_date_text, fill=text_color, font=font_small)

    # Save the generic cover
    img.save(cover_path)

# Function to attempt downloading a cover from Open Library
def fetch_from_open_library(isbn, cover_path):
    """Try to get the cover from Open Library using the ISBN."""
    if not isbn:
        return False
    
    try:
        open_library_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
        print(f"Trying Open Library: {open_library_url}")
        response = requests.get(open_library_url)
        
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(cover_path, 'JPEG')
            
            # Check if the file is valid
            if is_valid_file(cover_path):
                return True
            else:
                print(f"Open Library cover download failed (631 bytes) for ISBN {isbn}. Deleting.")
                os.remove(cover_path)
                return False
        else:
            print(f"Open Library did not return a valid cover for ISBN {isbn}.")
            return False
    except Exception as e:
        print(f"Error fetching cover from Open Library: {e}")
        return False

# Function to download cover using Google Books API
def download_cover(row):
    """Download book cover using ISBN first, and fallback to Title/Author. Also use Open Library if Google Books fails."""
    book_id = row['Book Id']
    title = clean_title(row['Title'])
    author = row['Author']
    isbn = clean_isbn(row['ISBN13'])
    published_year = row['Year Published']
    date =     row['Year Published']
    # URL encode the title and author to avoid issues with special characters
    encoded_title = quote(title)
    encoded_author = quote(author)

    # Set cover path using the book's ID
    cover_path = f"{cover_dir}/cover_{book_id}.jpg"
    
    # Check if cover already exists and is a valid file (also handle 631-byte failed files)
    if is_valid_file(cover_path):
        print(f"Cover for Book ID {book_id} already exists and is valid. Skipping download.")
        return cover_path

    # If no ISBN is available, attempt to get it from Open Library
    if not isbn:
        print(f"No ISBN found for {title}. Searching Open Library for an ISBN.")
        isbn = get_isbn_from_open_library(title, author)
        if isbn:
            print(f"Found ISBN {isbn} for {title}.")
        else:
            print(f"Could not find an ISBN for {title}.")
    
    try:
        # Step 1: Try using the ISBN if available (Google Books)
        if isbn:
            google_books_url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{quote(isbn)}"
            print(f"Trying ISBN search with Google Books: {google_books_url}")
            response = requests.get(google_books_url)
            if response.status_code == 200:
                book_data = response.json()
                
                # Check if 'items' exists in the response before accessing it
                if 'items' in book_data and len(book_data['items']) > 0:
                    # If only one result is returned, accept it immediately
                    volume_info = book_data['items'][0]['volumeInfo']
                    
                    if volume_info:
                        image_links = volume_info.get('imageLinks', {})
                        cover_url = image_links.get('large') or image_links.get('extraLarge') or image_links.get('thumbnail')
                        if cover_url:
                            # Fetch and save the cover image
                            response = requests.get(cover_url)
                            if response.status_code == 200:
                                img = Image.open(BytesIO(response.content))
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                img.save(cover_path, 'JPEG')
                                
                                # Check if the file is valid (handle 631-byte failed files)
                                if is_valid_file(cover_path):
                                    print(f"Downloaded cover for {title} via Google Books (Book ID {book_id}).")
                                    return cover_path
                                else:
                                    print(f"Google Books cover download failed (631 bytes) for {title}. Deleting.")
                                    os.remove(cover_path)
                else:
                    print(f"No items found for ISBN {isbn} in Google Books.")

        # Step 2: Fallback to Open Library if Google Books fails
        if isbn:
            if fetch_from_open_library(isbn, cover_path):
                print(f"Downloaded cover from Open Library for {title} (Book ID {book_id}).")
                return cover_path

        # Step 3: Try Google Books with Title/Author as a fallback if both ISBN methods fail
        google_books_url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{encoded_title}+inauthor:{encoded_author}"
        print(f"Trying Title/Author search with Google Books: {google_books_url}")
        response = requests.get(google_books_url)
        if response.status_code == 200:
            book_data = response.json()
            
            # Check if 'items' exists in the response before accessing it
            if 'items' in book_data and len(book_data['items']) > 0:
                # If only one result is returned, accept it immediately
                volume_info = book_data['items'][0]['volumeInfo']
                
                if volume_info:
                    image_links = volume_info.get('imageLinks', {})
                    cover_url = image_links.get('large') or image_links.get('extraLarge') or image_links.get('thumbnail')
                    if cover_url:
                        # Fetch and save the cover image
                        response = requests.get(cover_url)
                        if response.status_code == 200:
                            img = Image.open(BytesIO(response.content))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            img.save(cover_path, 'JPEG')
                            
                            # Check if the file is valid (handle 631-byte failed files)
                            if is_valid_file(cover_path):
                                print(f"Downloaded cover for {title} via Title/Author (Book ID {book_id}).")
                                return cover_path
                            else:
                                print(f"Google Books cover download failed (631 bytes) for {title}. Deleting.")
                                os.remove(cover_path)
            else:
                print(f"No items found for Title/Author search for {title} in Google Books.")
    except Exception as e:
        print(f"Error downloading cover for {title}: {e}")

    # If no cover was found, generate a generic cover and add to missing list
    generic_cover_path = f"{cover_dir}/GENERIC_{book_id}.jpg"
    print(f"No cover found for {title} (Book ID {book_id}). Generating a generic cover.")

    generate_generic_cover(title, author, date, generic_cover_path)
    missing_books.append((title, book_id, isbn))
    
    return generic_cover_path

# Function to generate report of missing covers
def generate_missing_books_report(missing_books):
    with open(not_found_report, 'w') as f:
        f.write("Books without found covers:\n\n")
        for book in missing_books:
            title, book_id, isbn = book
            f.write(f"Title: {title}, Book ID: {book_id}, ISBN: {isbn if isbn else 'N/A'}\n")

# Function to style graphs (using IBM-like fonts and AWS styling)
def style_graphs():
    plt.style.use('ggplot')  # Using ggplot style for a clean, polished look
    plt.rcParams.update({
        'font.size': 12,
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'font.family': 'DejaVu Sans',
    })


# Subclass FPDF to add headers, footers, and page borders
class PDF(FPDF):
    def header(self):
        # Adjust the starting position to allow content overlap
        self.set_y(10)
        # Set font
        self.set_font('Helvetica', 'B', 12)
        # Title (we'll leave some space at the top for overlapping)
        self.cell(0, 10, 'Goodreads Reading Report', ln=True, align='C')
        self.ln(5)
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Set font
        self.set_font('Helvetica', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    def add_page(self, *args, **kwargs):
        super().add_page(*args, **kwargs)
        # Add page border
        self.set_draw_color(0, 0, 0)  # Border color (black)
        self.rect(5, 5, self.w - 10, self.h - 10)  # Draw rectangle border

# Function to style graphs using Seaborn
def style_graphs():
    sns.set_theme(style="whitegrid")
    sns.set_palette("deep")
    plt.rcParams.update({
        'font.size': 10,
        'axes.labelsize': 10,
        'axes.titlesize': 12,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica']
    })

# Load and preprocess data
df = pd.read_csv('goodreads_library_export.csv')
df['Date Read'] = pd.to_datetime(df['Date Read'], errors='coerce')
df['Year Read'] = df['Date Read'].dt.year
df = df.dropna(subset=['Year Read'])
df['Number of Pages'] = df['Number of Pages'].fillna(0).astype(int)


# Subclass FPDF to add headers, footers, and page borders
class PDF(FPDF):
    def header(self):
        # Set font
        self.set_font('Helvetica', 'B', 12)
        # Title
        self.cell(0, 10, 'Goodreads Reading Report', ln=True, align='C')
        self.ln(5)
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Set font
        self.set_font('Helvetica', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    def add_page(self, *args, **kwargs):
        super().add_page(*args, **kwargs)
        # Add page border
        self.set_draw_color(0, 0, 0)  # Border color (black)
        self.rect(5, 5, self.w - 10, self.h - 10)  # Draw rectangle border

# Function to style graphs using Seaborn
def style_graphs():
    sns.set_theme(style="whitegrid")
    sns.set_palette("deep")
    plt.rcParams.update({
        'font.size': 10,
        'axes.labelsize': 10,
        'axes.titlesize': 12,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica']
    })

# Load and preprocess data
df = pd.read_csv('goodreads_library_export.csv')
df['Date Read'] = pd.to_datetime(df['Date Read'], errors='coerce')
df['Year Read'] = df['Date Read'].dt.year
df = df.dropna(subset=['Year Read'])
df['Number of Pages'] = df['Number of Pages'].fillna(0).astype(int)


# Subclass FPDF to add headers, footers, and page borders
class PDF(FPDF):
    def header(self):
        # Set font
        self.set_font('Helvetica', 'B', 12)
        # Title
        self.cell(0, 10, 'Goodreads Reading Report', ln=True, align='C')
        self.ln(5)
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Set font
        self.set_font('Helvetica', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    def add_page(self, *args, **kwargs):
        super().add_page(*args, **kwargs)
        # Add page border
        self.set_draw_color(0, 0, 0)  # Border color (black)
        self.rect(5, 5, self.w - 10, self.h - 10)  # Draw rectangle border

# Function to style graphs using Seaborn
def style_graphs():
    sns.set_theme(style="whitegrid")
    sns.set_palette("deep")
    plt.rcParams.update({
        'font.size': 10,
        'axes.labelsize': 10,
        'axes.titlesize': 12,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica']
    })

# Load and preprocess data
df = pd.read_csv('goodreads_library_export.csv')

# Parse 'Date Read' with error handling
df['Date Read'] = pd.to_datetime(df['Date Read'], errors='coerce')

# Create 'Year Read' from 'Date Read'
df['Year Read'] = df['Date Read'].dt.year

# Handle invalid or missing 'Date Read' by using 'Year Published'
df['Year Published'] = pd.to_numeric(df['Original Publication Year'], errors='coerce').fillna(0).astype(int)
df['Year Published'] = df['Year Published'].replace(0, pd.NA)  # Replace 0 with NaN if no year is available

# Create 'Year Categorized' column
df['Year Categorized'] = df['Year Read'].fillna(df['Year Published'])

# Drop rows where 'Year Categorized' is missing
df = df.dropna(subset=['Year Categorized'])

# Convert 'Year Categorized' to integer
df['Year Categorized'] = df['Year Categorized'].astype(int)

# Ensure 'Number of Pages' is an integer
df['Number of Pages'] = df['Number of Pages'].fillna(0).astype(int)






















# Subclass FPDF to add headers, footers, and page borders
class PDF(FPDF):
    def header(self):
        # Set font
        self.set_font('Helvetica', 'B', 12)
        # Title
        self.cell(0, 10, 'Goodreads Reading Report', ln=True, align='C')
        self.ln(5)
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Set font
        self.set_font('Helvetica', 'I', 8)
        # Page number
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    def add_page(self, *args, **kwargs):
        super().add_page(*args, **kwargs)
        # Add page border
        self.set_draw_color(0, 0, 0)  # Border color (black)
        self.rect(5, 5, self.w - 10, self.h - 10)  # Draw rectangle border

# Function to style graphs using Seaborn
def style_graphs():
    sns.set_theme(style="whitegrid")
    sns.set_palette("deep")
    plt.rcParams.update({
        'font.size': 10,
        'axes.labelsize': 10,
        'axes.titlesize': 12,
        'xtick.labelsize': 8,
        'ytick.labelsize': 8,
        'font.family': 'sans-serif',
        'font.sans-serif': ['Helvetica']
    })

# Load and preprocess data
df = pd.read_csv('goodreads_library_export.csv')

# Parse 'Date Read' with error handling
df['Date Read'] = pd.to_datetime(df['Date Read'], errors='coerce')

# Create 'Year Read' from 'Date Read'
df['Year Read'] = df['Date Read'].dt.year

# Convert 'Year Published' and 'Original Publication Year' to numeric, handling errors and missing values
df['Year Published'] = pd.to_numeric(df['Year Published'], errors='coerce')
df['Original Publication Year'] = pd.to_numeric(df['Original Publication Year'], errors='coerce')

# Calculate the latest year between 'Year Published' and 'Original Publication Year'
df['Latest Publication Year'] = df[['Year Published', 'Original Publication Year']].max(axis=1)

# Handle invalid or missing 'Date Read' by using 'Latest Publication Year'
df['Year Categorized'] = df['Year Read'].fillna(df['Latest Publication Year'])

# Drop rows where 'Year Categorized' is missing
df = df.dropna(subset=['Year Categorized'])

# Convert 'Year Categorized' to integer
df['Year Categorized'] = df['Year Categorized'].astype(int)

# **Filter out books published before the year 2000**
df = df[df['Year Categorized'] >= 2000]

# Ensure 'Number of Pages' is an integer
df['Number of Pages'] = df['Number of Pages'].fillna(0).astype(int)

# Initialize PDF
pdf = PDF()
pdf.set_auto_page_break(auto=True, margin=15)

# Title page
pdf.add_page()
pdf.set_font('Helvetica', 'B', 20)
pdf.cell(0, 80, txt="Goodreads Reading Report", ln=True, align='C')
pdf.set_font('Helvetica', '', 14)
pdf.cell(0, 10, txt="An overview of your reading activity", ln=True, align='C')

# Style and generate graphs
style_graphs()

# Plot "Books per Year"
plt.figure(figsize=(8, 6))
books_per_year = df.groupby('Year Categorized').size()
sns.barplot(x=books_per_year.index.astype(int), y=books_per_year.values, color='#0072C6')
plt.title('Books per Year')
plt.xlabel('Year')
plt.ylabel('Number of Books')
plt.tight_layout()
plt.savefig('books_per_year.png', dpi=300)
plt.close()

# Plot "Pages per Year"
plt.figure(figsize=(8, 6))
pages_per_year = df.groupby('Year Categorized')['Number of Pages'].sum()
sns.barplot(x=pages_per_year.index.astype(int), y=pages_per_year.values, color='#FF9900')
plt.title('Pages per Year')
plt.xlabel('Year')
plt.ylabel('Total Pages Read')
plt.tight_layout()
plt.savefig('pages_per_year.png', dpi=300)
plt.close()

# Add graphs to PDF
pdf.add_page()
pdf.image('books_per_year.png', x=15, y=20, w=180)
pdf.add_page()
pdf.image('pages_per_year.png', x=15, y=20, w=180)

# Summary Table
pdf.add_page()
pdf.set_font('Helvetica', 'B', 14)
pdf.cell(0, 10, txt="Reading Summary per Year", ln=True, align='C')
pdf.ln(5)

# Create a DataFrame for summary
summary_df = pd.DataFrame({
    'Books': books_per_year,
    'Pages': pages_per_year
}).reset_index().rename(columns={'Year Categorized': 'Year'})
summary_df['Year'] = summary_df['Year'].astype(int)

# Add summary table
pdf.set_font('Helvetica', '', 12)
col_widths = [30, 50, 50]
pdf.set_fill_color(200, 200, 200)
pdf.cell(col_widths[0], 10, 'Year', border=1, fill=True, align='C')
pdf.cell(col_widths[1], 10, 'Books Read', border=1, fill=True, align='C')
pdf.cell(col_widths[2], 10, 'Pages Read', border=1, fill=True, align='C')
pdf.ln()
for index, row in summary_df.iterrows():
    pdf.cell(col_widths[0], 10, str(row['Year']), border=1, align='C')
    pdf.cell(col_widths[1], 10, str(row['Books']), border=1, align='C')
    pdf.cell(col_widths[2], 10, str(row['Pages']), border=1, align='C')
    pdf.ln()

# Add book cards organized by 'Year Categorized'
pdf.set_font('Helvetica', 'B', 14)
pdf.add_page()
pdf.cell(0, 10, txt="Books by Year", ln=True, align='C')
pdf.ln(5)

def add_book_cards(pdf, df, year):
    # Adjusted card size (reduced to 50% of original size)
    original_card_width = 60
    original_card_height = 90
    reduction_factor = 0.5  # Reduce size to 50% of original
    card_width = original_card_width * reduction_factor  # 30
    card_height = original_card_height * reduction_factor  # 45
    margin = 5  # Adjusted margin

    # Starting positions
    x_start = pdf.l_margin
    y_start = pdf.get_y()
    x = x_start
    y = y_start

    # Calculate available width and number of columns
    available_width = pdf.w - pdf.l_margin - pdf.r_margin
    num_columns = int((available_width + margin) // (card_width + margin))
    if num_columns < 1:
        num_columns = 1

    # Recalculate margin to evenly distribute the cards
    total_card_width = num_columns * card_width
    total_margin = available_width - total_card_width
    if num_columns > 1:
        margin = total_margin / (num_columns - 1)
    else:
        margin = total_margin

    row_height = card_height + 18  # Adjusted for text area

    for index, row in df.iterrows():
        title = row['Title']
        author = row['Author']
        pages = row['Number of Pages']
        date_read = row['Date Read']
        latest_pub_year = row['Latest Publication Year']

        if pd.notna(date_read):
            date_info = f"Read: {date_read.date()}"
        else:
            date_info = f"Latest Pub: {int(latest_pub_year)}"

        cover_path = download_cover(row)

        # Draw the book card
        if cover_path and os.path.exists(cover_path):
            pdf.image(cover_path, x=x, y=y, w=card_width, h=card_height)
        else:
            pdf.rect(x, y, card_width, card_height)

        # Save current x and y positions
        x_current = x
        y_current = y + card_height + 2

        # Move to below the image
        pdf.set_xy(x_current, y_current)

        # Set font sizes adjusted for smaller card size
        pdf.set_font('Helvetica', 'B', 6)
        # Title
        pdf.multi_cell(card_width, 3, title, align='C')

        # Restore x position after multi_cell
        y_text = pdf.get_y()
        pdf.set_xy(x_current, y_text)

        # Author
        pdf.set_font('Helvetica', '', 5)
        pdf.multi_cell(card_width, 3, f"by {author}", align='C')

        # Restore x position after multi_cell
        y_text = pdf.get_y()
        pdf.set_xy(x_current, y_text)

        # Pages and Date Info
        pdf.set_font('Helvetica', '', 4)
        pdf.cell(card_width, 3, f"{pages} pages", ln=1, align='C')
        pdf.set_x(x_current)
        pdf.cell(card_width, 3, date_info, ln=1, align='C')

        # Move position to the next column
        x += card_width + margin
        if x + card_width > pdf.w - pdf.r_margin:
            # Move to next row
            x = x_start
            y += row_height
            if y + row_height > pdf.page_break_trigger:
                pdf.add_page()
                y = pdf.get_y()  # Reset y to current position after header
                x = x_start  # Reset x to the left margin

    # Reset position
    pdf.set_xy(x_start, y + row_height)

# Group books by 'Year Categorized' and add them to the PDF
for year in sorted(df['Year Categorized'].unique(), reverse=True):
    year_df = df[df['Year Categorized'] == year]
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, txt=f"Books in {int(year)}", ln=True, align='C')
    pdf.ln(5)
    add_book_cards(pdf, year_df, year)

# Output the PDF
pdf.output('goodreads_professional_report.pdf')

# Clean up chart images
os.remove('books_per_year.png')
os.remove('pages_per_year.png')

# Generate missing books report
generate_missing_books_report(missing_books)