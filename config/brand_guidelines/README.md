# Brand Guidelines Storage

This directory stores uploaded brand guidelines documents for use in Trust Stack analysis.

## Structure

```
brand_guidelines/
├── {brand_id}/
│   ├── guidelines.txt          # Processed text from uploaded document
│   ├── metadata.json           # Upload metadata and statistics
│   └── original/               # (Optional) Original uploaded files
│       └── {original_filename}
```

## Usage

Brand guidelines are automatically loaded during Coherence scoring to provide context-aware brand voice consistency checks.

### Uploading Guidelines

1. Navigate to the "Brand Guidelines" section in the webapp
2. Select your brand
3. Upload PDF, DOCX, or TXT file containing brand voice/style guidelines
4. Guidelines are processed and stored automatically

### What Gets Extracted

- Brand voice and tone guidelines
- Vocabulary preferences
- Style rules and conventions
- Writing standards
- Any other brand-specific content guidance

## File Formats Supported

- **PDF** (.pdf) - Extracts text from all pages
- **DOCX** (.docx) - Extracts paragraphs and tables
- **TXT** (.txt) - Plain text files

## Metadata

Each brand's `metadata.json` contains:

```json
{
  "brand_id": "example_brand",
  "original_filename": "Brand_Guidelines_2024.pdf",
  "upload_date": "2025-11-20T10:25:00-05:00",
  "file_size_bytes": 2458624,
  "word_count": 5420,
  "character_count": 32500,
  "version": "1.0"
}
```

## How It's Used

During Coherence scoring, the LLM receives:
1. The content being analyzed
2. The brand's uploaded guidelines
3. Instructions to compare content against specific brand standards

This enables accurate, brand-specific suggestions like:
> "Change 'Find the right card' → 'Discover your card'. This aligns with your brand guideline (p.12): 'Use "discover" over "find" to convey empowerment.'"

## Management

- **View**: See current guidelines in the webapp
- **Update**: Upload a new file to replace existing guidelines
- **Delete**: Remove guidelines via the webapp interface
