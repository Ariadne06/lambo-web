# PDF Templates Organization

This directory contains all PDF template generators organized by category.

## Directory Structure

```
pdf_templates/
├── base.py                    # Shared utilities (headers, watermarks, styles)
├── resident/                  # Resident-related PDFs
│   ├── resident_detail.py
│   ├── resident_list.py
│   ├── resident_list_filtered.py
│   └── resident_statistics.py
├── household/                 # Household/Family-related PDFs
│   └── (future templates)
├── child_health/             # Child Health-related PDFs
│   └── (future templates)
├── maternal_health/          # Maternal Health-related PDFs
│   └── (future templates)
├── business/                 # Business-related PDFs
│   └── clearance_applications.py
└── financial/                # Financial-related PDFs
    └── revenue_report.py
```

## Usage

### Importing Templates

When importing PDF templates from other modules, use the new folder structure:

```python
# Resident templates
from reports_module.pdf_templates.resident.resident_detail import generate_resident_detail_pdf
from reports_module.pdf_templates.resident.resident_list_filtered import generate_resident_list_pdf

# Business templates
from reports_module.pdf_templates.business.clearance_applications import ClearanceApplicationsReport

# Financial templates
from reports_module.pdf_templates.financial.revenue_report import RevenueReport
```

### Within PDF Templates

When importing base utilities within a PDF template:

```python
# Use relative import from parent directory
from ..base import draw_barangay_header, get_standard_styles, draw_watermark
```

## Categories

### RESIDENT

Templates related to individual resident records and information.

- `resident_detail.py` - Individual resident profile PDF
- `resident_list.py` - General resident list PDF
- `resident_list_filtered.py` - Filtered resident list with applied filters
- `resident_statistics.py` - Resident statistics and demographics

### HOUSEHOLD/FAMILY

Templates related to household and family records.

- Currently empty - ready for future household reports

### CHILD HEALTH

Templates related to child health records and monitoring.

- Currently empty - ready for future child health reports

### MATERNAL HEALTH

Templates related to maternal health records and monitoring.

- Currently empty - ready for future maternal health reports

### BUSINESS

Templates related to business permits, clearances, and registrations.

- `clearance_applications.py` - Business clearance applications report

### FINANCIAL

Templates related to financial reports, revenue, and transactions.

- `revenue_report.py` - Revenue and financial summary report

## Adding New Templates

1. Determine which category your template belongs to
2. Create the template file in the appropriate folder
3. Import base utilities: `from ..base import draw_barangay_header, get_standard_styles, draw_watermark`
4. Follow the existing naming convention: `[category]_[template_name].py`
5. Document the template in this README

## Common Utilities (base.py)

All templates have access to shared utilities:

- `draw_barangay_header()` - Standard barangay header with logo
- `draw_watermark()` - Diagonal watermark for documents
- `get_standard_styles()` - Times-Roman paragraph styles
- `get_standard_table_style()` - Standard table formatting

## Best Practices

1. Use Times-Roman font family for consistency
2. Include watermarks for official documents
3. Use standard barangay header on all PDFs
4. Follow A4 page size (portrait or landscape as needed)
5. Include generation date and page numbers
6. Use color scheme: Burgundy (#991B1B) for headers
