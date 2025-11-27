# Reports Module - LAMBO Barangay Management System

## Overview

The `reports_module` is a Django app for generating PDF reports using ReportLab. It provides a flexible framework for creating various barangay management reports with customizable filters and parameters.

## Structure

```
reports_module/
├── __init__.py
├── apps.py
├── admin.py
├── models.py
├── tests.py
├── urls.py
├── views.py
├── utils/
│   ├── __init__.py
│   └── database_helpers.py          # Raw SQL queries to PostgreSQL
├── pdf_templates/
│   ├── __init__.py
│   ├── base.py                      # Base PDF generator class
│   ├── resident_statistics.py      # Resident statistics report
│   ├── clearance_applications.py   # Clearance applications report
│   └── revenue_report.py            # Revenue/financial report
└── templates/
    └── reports_module/
        └── sample_test.html          # Test page with report buttons
```

## Features

### 1. Database Helpers (`utils/database_helpers.py`)

- Raw SQL query execution
- PostgreSQL stored procedure integration
- Helper functions for common report queries:
  - `get_resident_statistics()` - Demographics and voter data
  - `get_clearance_applications_report()` - Application listings
  - `get_revenue_report()` - Financial summaries
  - `get_household_statistics()` - Household data
  - `get_blotter_report()` - Incident records
- Formatting utilities for dates and currency

### 2. PDF Templates (`pdf_templates/`)

All PDF generators inherit from `BasePDFGenerator` which provides:

- Consistent styling and formatting
- Header/footer templates with barangay branding
- Table generation utilities
- Custom paragraph styles

**Available Report Templates:**

- **Resident Statistics Report** - Demographics, gender breakdown, voter registration
- **Clearance Applications Report** - Filterable list of clearance applications
- **Revenue Report** - Financial summary and transaction statistics

### 3. API Endpoints

#### Test Page

```
GET /reports/test/
```

Interactive HTML page with buttons to generate each report type.

#### API Endpoints (Programmatic Access)

```
GET /reports/api/resident-statistics/
GET /reports/api/clearance-applications/
GET /reports/api/revenue/
```

#### Template-Friendly URLs

```
GET /reports/resident-statistics/
GET /reports/clearance-applications/
GET /reports/revenue/
```

### 4. Query Parameters

**Common Parameters:**

- `date_from` - Start date filter (YYYY-MM-DD)
- `date_to` - End date filter (YYYY-MM-DD)

**Report-Specific Parameters:**

- `status` - Filter by application status (clearance applications only)

**Example:**

```
/reports/api/clearance-applications/?date_from=2025-01-01&date_to=2025-11-24&status=Approved
```

## Usage

### 1. Access the Test Page

Navigate to: `http://localhost:8000/reports/test/`

This page provides a user-friendly interface with:

- Date range pickers for each report
- Status filters (where applicable)
- One-click PDF generation buttons

### 2. Generate Reports Programmatically

**Python Example:**

```python
from reports_module.pdf_templates.resident_statistics import ResidentStatisticsReport

# Generate report
report = ResidentStatisticsReport(date_from='2025-01-01', date_to='2025-11-24')
pdf_buffer = report.generate()

# Save to file
with open('resident_stats.pdf', 'wb') as f:
    f.write(pdf_buffer.getvalue())
```

**API Call Example (curl):**

```bash
curl -X GET "http://localhost:8000/reports/api/resident-statistics/?date_from=2025-01-01&date_to=2025-11-24" \
     -o resident_statistics.pdf
```

### 3. Add Custom Reports

**Step 1: Create Database Helper**
Add your query function to `utils/database_helpers.py`:

```python
def get_custom_report_data(param1, param2):
    query = "SELECT * FROM your_table WHERE ..."
    return execute_query(query, [param1, param2])
```

**Step 2: Create PDF Template**
Create `pdf_templates/custom_report.py`:

```python
from .base import BasePDFGenerator
from ..utils.database_helpers import get_custom_report_data

class CustomReport(BasePDFGenerator):
    def __init__(self, param1=None, param2=None):
        super().__init__(title="Custom Report")
        self.param1 = param1
        self.param2 = param2

    def generate(self):
        doc = SimpleDocTemplate(self.buffer, ...)
        story = []

        # Add title
        story.append(Paragraph("CUSTOM REPORT", self.styles['CustomTitle']))

        # Get data
        data = get_custom_report_data(self.param1, self.param2)

        # Build table
        table_data = [['Header1', 'Header2']]
        for row in data:
            table_data.append([row['field1'], row['field2']])

        story.append(self.create_table(table_data))

        # Build PDF
        doc.build(story, onFirstPage=self.create_header, onLaterPages=self.create_header)
        self.buffer.seek(0)
        return self.buffer
```

**Step 3: Add View**
In `views.py`:

```python
from .pdf_templates.custom_report import CustomReport

class GenerateCustomReport(APIView):
    def get(self, request):
        param1 = request.GET.get('param1', None)
        param2 = request.GET.get('param2', None)

        report = CustomReport(param1=param1, param2=param2)
        pdf_buffer = report.generate()

        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="custom_report.pdf"'
        return response
```

**Step 4: Add URL Route**
In `urls.py`:

```python
path('api/custom-report/', views.GenerateCustomReport.as_view(), name='api_custom_report'),
```

**Step 5: Add Test Button**
Update `templates/reports_module/sample_test.html` to include your new report button.

## Styling Customization

The `BasePDFGenerator` class provides these custom styles:

- `CustomTitle` - Large centered title (18pt, bold)
- `CustomSubtitle` - Medium centered subtitle (12pt)
- `CustomHeader` - Section headers (14pt, bold)
- `CustomBody` - Body text (10pt, justified)
- `CustomSmall` - Small text/footnotes (8pt)

Customize in `pdf_templates/base.py`:

```python
self.styles.add(ParagraphStyle(
    name='YourStyle',
    fontSize=12,
    textColor=colors.HexColor('#1f2937'),
    alignment=TA_LEFT,
    fontName='Helvetica-Bold'
))
```

## Header/Footer Customization

Edit the `create_header()` and `create_footer()` methods in `pdf_templates/base.py`:

```python
def create_header(self, canvas, doc):
    canvas.saveState()
    # Add your barangay logo
    canvas.drawImage('static/images/logo.png', ...)
    # Add barangay name
    canvas.drawCentredString(self.width / 2, self.height - 0.75*inch, 'BARANGAY NAME')
    canvas.restoreState()
```

## Database Integration

The module uses raw SQL queries to PostgreSQL stored procedures via `utils/database_helpers.py`.

**Key Functions:**

- `execute_query(query, params)` - Execute any SQL query
- Format helpers: `format_datetime_for_report()`, `format_currency()`

**Example Query:**

```python
def get_data():
    query = """
        SELECT * FROM get_all_applications()
        WHERE created_at >= %s AND created_at <= %s
    """
    return execute_query(query, [date_from, date_to])
```

## Testing

Run Django tests:

```bash
python manage.py test reports_module
```

Add test cases in `tests.py`:

```python
from django.test import TestCase
from .pdf_templates.resident_statistics import ResidentStatisticsReport

class ReportTests(TestCase):
    def test_resident_statistics_generation(self):
        report = ResidentStatisticsReport()
        pdf = report.generate()
        self.assertIsNotNone(pdf)
```

## Deployment Considerations

1. **PDF Fonts**: Ensure system fonts are available on the deployment server
2. **File Permissions**: Verify temp directory write access for PDF generation
3. **Memory**: Large reports may require increased memory limits
4. **Async Generation**: For very large reports, consider using Celery for background processing

## Dependencies

- `reportlab>=4.2.5` - PDF generation library
- `Django>=5.1.7` - Web framework
- `djangorestframework>=3.16.0` - REST API support
- `psycopg2-binary>=2.9.10` - PostgreSQL adapter

## Future Enhancements

- [ ] Add chart/graph generation using ReportLab graphics
- [ ] Implement Excel export option
- [ ] Add report scheduling/automation
- [ ] Create report templates for blotter records
- [ ] Add data visualization dashboards
- [ ] Implement report caching for frequently generated reports
- [ ] Add email delivery option for reports

## Support

For issues or questions about the reports module, contact the development team or refer to the LAMBO project documentation.
