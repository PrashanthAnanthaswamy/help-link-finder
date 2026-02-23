# CSV Upload Folder

Upload your CSV files here to use with the Help Link Finder.

## How to Upload via GitHub (Drag & Drop)

1. Click **"Add file"** (top-right of this page) → **"Upload files"**
2. **Drag and drop** your `.csv` file into the upload area
3. Click **"Commit changes"**
4. Go to **Actions** → **Help Link Finder** → **Run workflow**
5. Set **Input mode** to `csv`
6. Set **CSV file path** to `inputs/your_file.csv`
7. Click **Run workflow**

## CSV Format

Your CSV file needs a `url` column header. Example:

```csv
url
https://www.zennioptical.com/
https://www.zennioptical.com/c/all-glasses
https://www.zennioptical.com/kids-glasses
```

A header-only format also works (first column is used if no `url` header is found).

## Default CSV

The default file used by the workflow is `sample_urls.csv` in the repo root.
