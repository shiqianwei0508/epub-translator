
import ebooklib
from ebooklib import epub

import warnings
# 忽略特定警告
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=FutureWarning, module='ebooklib')

def modify_epub_title(input_file, output_file, new_title):
    # Read the original EPUB file
    book = epub.read_epub(input_file)

    # Check if the book contains content
    if not book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        print("Warning: The book has no document items.")
        return

    # Change the title
    book.set_title(new_title)

    # Try to write the modified EPUB to a new file
    try:
        epub.write_epub(output_file, book)
        print(f"EPUB file has been modified and saved as {output_file}")
    except Exception as e:
        print(f"Error saving updated EPUB file: {e}")

# Usage Example
input_file = 'Python编程与初级数学.epub'  # Path to the original EPUB file
output_file = 'Python初级数学与编程.epub'  # Path for the modified EPUB file
new_title = 'Python初级数学与编程'           # The new title you want to set

modify_epub_title(input_file, output_file, new_title)