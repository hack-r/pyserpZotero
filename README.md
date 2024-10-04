# ![](https://i.imgur.com/bHS0mPZs.png) pyserpZotero 


![](/Users/user/PycharmProjects/pyserpZotero/src/pyserpZotero/feature_header.png)
Installation:
`pip install pyserpZotero`

Usage:
`psz`

Google Scholar citation download, parsing, Bibtex export, search for free PDFs, and Zotero cloud upload. SerpAPI is leveraged for stable access to Google Scholar without IP throttling.

| Resource     | URL                                    |
| ------------ | -------------------------------------- |
| Docs         | https://pyserpzotero.readthedocs.io    |
| GitHub Repo  | https://github.com/hack-r/pyserpZotero |
| PyPI Package | https://pypi.org/project/pyserpZotero/ |
| SerpAPI      | https://serpAPI.com                    |
| Zotero       | https://zotero.org                     |

## What does it do?

_pyserpZotero_ is a Python library designed to automate the search, management of scholarly literature citations, and attachment of free PDFs to Zotero citations. It leverages SerpAPI for reliable access to Google Scholar and utilizes the Zotero service for efficient citation management. The library simplifies the process of searching for academic papers, downloading them (where available for free), and organizing citations directly into your Zotero library.

_pyserpZotero_ offers the following functions for (semi-) automating literature review tasks:

- _SerpZot_ (class) - Instantiates a SerpZot object for API management.
  - **SearchScholar** - Searches Google Scholar for papers corresponding to 1 or more search terms and captures their identifiers.
  - **Search2Zotero** - Pulls references from Google using identifiers from _SearchScholar_, converts to Bibtex via CrossRef, reformats for Zotero, looks for PDFs, and uploads to your Zotero cloud library (results will automatically sync to the desktop client, if installed).
  - **CleanZot** - Attempt to remove/replace broken LaTex and other formatting in titles.

## How to configure it?

You'll need to provide an API key for serpAPI and Zotero, as well as a Zotero library Id. You can either provide these directly as arguments to
the functions, via the interactive mode, or manage them more securely via a YAML configuration file, as in the _Example Usage_ below.

Yes, considering the addition of the GUI to your `pyserpZotero` project, it is highly recommended to update the `README.md` to reflect this new feature. Updating the `README.md` will help users understand the full capabilities of your tool, how to install it, and how to use both the CLI and GUI interfaces.

Below are suggestions for updating your `README.md`:

---

**pyserpZotero** is a Python library and application designed to automate the search and management of scholarly literature citations, as well as the attachment of free PDFs to Zotero citations. It leverages the power of SerpAPI for reliable access to Google Scholar and utilizes the Zotero service for efficient citation management. The tool simplifies the process of searching for academic papers, downloading them (where available for free), and organizing citations directly into your Zotero library.

### Key Features

- **GUI and CLI Interfaces**: Offers both a user-friendly graphical interface and a command-line interface for flexibility.
- **Automated Search**: Search Google Scholar and preprint servers like arXiv, medRxiv, and bioRxiv.
- **Citation Management**: Automatically fetches citations and uploads them to your Zotero library.
- **PDF Attachment**: Attempts to find and download free PDFs of the articles and attach them to the Zotero entries.
- **Duplicate Avoidance**: Checks your Zotero library to avoid adding duplicate entries.

## Installation

```bash
pip install pyserpZotero
```

Ensure you have the following dependencies installed:

- Python 3.7 or higher
- Required Python packages will be installed automatically via `pip`.

## Usage

### Graphical User Interface (GUI)

Starting with version **1.2**, `pyserpZotero` includes a GUI application for an improved user experience.

#### Launching the GUI

After installation, you can start the GUI by running:

```bash
pyserpZotero_gui
```

#### Features of the GUI

- **Easy Configuration**: Input your SerpAPI and Zotero credentials directly in the GUI.
- **Multiple Search Terms**: Enter multiple search terms separated by semicolons (`;`).
- **Progress Monitoring**: View real-time progress of your searches and downloads.
- **Log Viewer**: See detailed logs of the operations being performed.
- **PDF Viewer**: Open and view downloaded PDFs directly from the application.

### Command-Line Interface (CLI)

For users who prefer the command line, `pyserpZotero` still offers a robust CLI.

#### Starting the CLI

Simply run:

```bash
psz
```

#### Interactive Mode

The CLI will prompt you for:

- SerpAPI Key
- Zotero Library ID
- Zotero API Key
- Download preferences
- Search terms

#### Example Usage

```bash
Enter your SerpAPI API key:
Enter your Zotero library ID:
Enter your Zotero API key:
Enter download destination path (leave empty for current directory):
Do you want to download your citation library to avoid duplicating entries? [Y/n]:
Do you want to download PDFs? [Y/n]:
Enter the oldest year to search from (leave empty if none):
Enter the max number of searches you would like to do (leave empty for default value of 50):
Enter up to 20 search phrases separated by semi-colon(;): Cancer Research; Humanoid Robot; DNA mutation
```

## Configuration

You can provide your API keys and preferences either during the interactive prompts or by editing the `config.yaml` file created in your current directory.

### `config.yaml` Example

```yaml
SERP_API_KEY: your_serpapi_key
ZOT_ID: your_zotero_library_id
ZOT_KEY: your_zotero_api_key
DOWNLOAD_DEST: ./downloads
ENABLE_LIB_DOWNLOAD: true
ENABLE_PDF_DOWNLOAD: true
NO_SERP: false
NO_ARXIV: false
NO_BIOARXIV: false
NO_MEDARXIV: false
```

## Advanced Features

### Skipping Specific Platforms

You can configure the application to skip searching specific platforms by setting the following options in your `config.yaml`:

- `NO_SERP: true` - Skip searching using SerpAPI (Google Scholar).
- `NO_ARXIV: true` - Skip searching on arXiv.
- `NO_BIOARXIV: true` - Skip searching on bioRxiv.
- `NO_MEDARXIV: true` - Skip searching on medRxiv.

### Multiple Queries

You can add multiple queries separated by semicolons (`;`). The application will process each query sequentially.

### PDF Viewer

The GUI includes a built-in PDF viewer. After downloading PDFs, you can open and view them directly from the application.

## Dependencies

Make sure to have the following packages installed:

- **ttkbootstrap**: For enhanced GUI styling.
  ```bash
  pip install ttkbootstrap
  ```
- **PyMuPDF**: For PDF viewing functionality.
  ```bash
  pip install PyMuPDF
  ```

### Why use SerpAPI?

SerpAPI provides stable access to Google Scholar without IP throttling, ensuring that your searches are reliable and uninterrupted.

### How do I obtain API keys?

- **SerpAPI Key**: Sign up at [SerpAPI](https://serpapi.com) to get your API key.
- **Zotero API Key**: Log in to your Zotero account and navigate to [API Settings](https://www.zotero.org/settings/keys) to create a new key.

### Is there a free tier for SerpAPI?

Yes, SerpAPI offers a free tier which currently allows for 100 searches per month.

## Why do you sometimes align assignment operators across lines like that?

It's an R programming practice for readability based on major style guides (not PEP).

## Contributing

Contributions and forks are welcome! Please see the [GitHub repository](https://github.com/hack-r/pyserpZotero) for contribution guidelines. 

## License

This project is licensed under the MIT License.
