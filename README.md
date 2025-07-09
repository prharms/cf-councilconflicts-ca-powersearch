# Political Potential Conflict of Interest Analysis Tool

A comprehensive Python program that analyzes potential conflicts of interest by systematically examining overlapping relationships between vote beneficiaries and campaign contributors. This analysis identifies patterns that warrant further investigation, not determinations of wrongdoing.

## Analysis Scope

This tool systematically examines overlapping relationships between political vote beneficiaries and campaign contributors using advanced fuzzy matching and AI validation. Results represent patterns that warrant further investigation, not determinations of wrongdoing.

## Key Features

- **AI-Powered Validation**: Claude 4 Sonnet integration for intelligent false positive filtering
- **Advanced Fuzzy Matching**: Multi-algorithm approach with configurable 85% default threshold
- **Comprehensive Entity Matching**: Compares both contributor names and employer information
- **Smart Normalization**: Handles business suffixes, "doing business as" patterns, and union variations
- **Automated Processing**: Automatically detects politician names from data
- **Multiple Output Formats**: Summary, detailed, and CSV reports
- **Government Employee Filtering**: Excludes government/academic employees per conflict of interest rules
- **Professional Architecture**: Modular design with dependency injection and comprehensive type safety

## Project Structure

```
minutes_cf_compare/
├── scripts/
│   └── compare_beneficiaries.py    # Compatibility wrapper (deprecated)
├── src/political_conflict_analysis/
│   ├── __init__.py                 # Package initialization
│   ├── __main__.py                 # Main entry point
│   ├── analyzers.py                # Main analysis orchestration
│   ├── matchers.py                 # Fuzzy matching implementation
│   ├── validators.py               # Claude AI validation
│   ├── normalizers.py              # Entity normalization
│   ├── processors.py               # Data processing
│   ├── report_generator.py         # Report generation
│   ├── types.py                    # Type definitions
│   └── py.typed                    # Type information marker
├── tests/                          # Test suite
├── docs/                           # Documentation
│   └── ARCHITECTURE.md            # Technical architecture details
├── data/                          # Input data files (gitignored)
│   ├── minutes.csv                # Meeting minutes data (user-provided)
│   └── campaign_finance.csv       # Campaign finance data (user-provided)
├── output/                        # Generated reports (gitignored)
├── logs/                          # Application logs (gitignored)
├── pyproject.toml                 # Modern Python packaging configuration
├── requirements.txt               # Python dependencies
├── env_template.txt               # Environment configuration template
├── .env                          # Environment configuration (create from template, gitignored)
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

**Note**: The `data/`, `output/`, `logs/` folders and `.env` file are excluded from version control for security and privacy. Users must provide their own data files and create their `.env` configuration.

## Installation

1. **Prerequisites**: Python 3.8 or higher

2. **Install Package**:
   ```bash
   # Install in development mode
   pip install -e .
   
   # Or install development dependencies
   pip install -e ".[dev]"
   ```

3. **Set up Environment**:
   ```bash
   # Copy the environment template
   cp env_template.txt .env
   
   # Edit .env and add your Anthropic API key
   # ANTHROPIC_API_KEY=your_api_key_here
   ```

## Claude AI Validation

The system requires Claude 4 Sonnet for AI-powered validation to filter false positives and ensure high-quality results.

### Setup

1. **Get Claude API Key**: Sign up at [Anthropic Console](https://console.anthropic.com/)
2. **Configure Environment**: Add your API key to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
   ```

### How It Works

Claude analyzes each potential conflict using sophisticated reasoning:
- **Entity Identity Analysis**: Determines if beneficiary and contributor are truly the same organization
- **Government Employee Rules**: Automatically excludes government/academic employees
- **Labor Union Relationships**: Identifies related union entities
- **Business Context Understanding**: Distinguishes between similar but separate organizations

### Benefits

- **High Precision**: Filters out false positives like "Greater Riverside Chamber" vs "Riverside County Black Chamber"
- **Intelligent Context**: Understands "doing business as" relationships and corporate structures
- **Rule-Based Logic**: Applies consistent conflict of interest principles
- **Scalable Analysis**: No hardcoded examples - uses general reasoning frameworks

## Usage

### Basic Usage

```bash
# Using the installed command
political-conflict-analysis \
    --minutes minutes.csv \
    --campaign-finance campaign_finance.csv \
    --output-dir output

# Or using python -m
python -m political_conflict_analysis \
    --minutes minutes.csv \
    --campaign-finance campaign_finance.csv \
    --output-dir output
```

This will:
- Automatically detect the politician from the data
- Use 85% similarity threshold (default)
- Apply Claude AI validation
- Generate comprehensive reports

### Advanced Usage

**Custom threshold:**
```bash
political-conflict-analysis \
    --minutes minutes.csv \
    --campaign-finance campaign_finance.csv \
    --threshold 90 \
    --output-dir output
```

**Custom output directory:**
```bash
political-conflict-analysis \
    --minutes minutes.csv \
    --campaign-finance campaign_finance.csv \
    --output-dir results/
```

**Test API connection:**
```bash
political-conflict-analysis \
    --minutes minutes.csv \
    --campaign-finance campaign_finance.csv \
    --test-api
```

**Verbose logging:**
```bash
political-conflict-analysis \
    --minutes minutes.csv \
    --campaign-finance campaign_finance.csv \
    --log-level DEBUG \
    --output-dir output
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--minutes` | Path to meeting minutes CSV file | **Required** |
| `--campaign-finance` | Path to campaign finance CSV file | **Required** |
| `--threshold` | Fuzzy matching threshold (0-100) | `85.0` |
| `--output-dir` | Output directory for reports | `output` |
| `--log-level` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `--test-api` | Test Claude API connection and exit | `False` |

## Input Data Format

### Meeting Minutes CSV

Required columns:
- `Meeting Date`: Date of the meeting (YYYY-MM-DD or MM/DD/YYYY)
- `Item Description`: Description of the agenda item  
- `[Politician Name] Vote`: Politician's vote (AYE, NAY, ABSENT, ABSTAIN, RECUSED)
- `Vote Outcome`: Result (PASSED, FAILED)
- `Beneficiary`: Entity that benefits from the agenda item

Example:
```csv
Meeting Date,Item Description,Cervantes Vote,Vote Outcome,Beneficiary
5/23/2022,Franchise agreement for waste collection,AYE,PASSED,ABC Services Inc.
6/02/2024,Planning permit for gas station facility,AYE,PASSED,Bob Jones of XYZ Enterprises
```

### Campaign Finance CSV

Required columns:
- `Start Date`: Contribution date
- `Contributor`: Name of the contributor
- `Employer`: Employer of the contributor (optional)
- `Amount`: Contribution amount
- `Transaction Type`: Type of contribution
- `Office`: Office being sought (optional)

Example:
```csv
Start Date,Contributor,Employer,Amount,Transaction Type,Office
2024-08-30,ABC Services,,500.00,Monetary Contribution,City Council
2024-02-23,Jones John,XYZ Enterprises,2000.00,Monetary Contribution,City Council
```

## Output Reports

### Summary Report (`politician_conflicts_summary.txt`)

High-level overview including:
- Total potential conflicts found
- Total contribution amounts
- Top conflicts by contribution amount
- Analysis metadata

### Detailed Report (`politician_conflicts_detailed.txt`)

Comprehensive analysis with:
- Full beneficiary and contributor details
- Vote histories and outcomes
- Contribution details with dates and amounts
- Similarity scores and match types

### CSV Export (`politician_conflicts.csv`)

Machine-readable format for further analysis:
- All conflict data in structured format
- Suitable for spreadsheet analysis
- Enables custom reporting and visualization

## Matching Algorithm

### Multi-Stage Process

1. **Data Loading & Validation**
   - CSV parsing with error handling
   - Data type validation
   - Missing data detection

2. **Entity Normalization**
   - Business suffix handling
   - "Doing business as" pattern extraction
   - Union name standardization
   - "Person of Company" pattern processing

3. **Fuzzy Matching**
   - WRatio (40% weight): Overall similarity
   - Partial Ratio (30% weight): Substring matches
   - Token Sort Ratio (20% weight): Word order independence
   - Token Set Ratio (10% weight): Set-based comparison

4. **AI Validation**
   - Entity identity analysis
   - Government employee exclusion
   - Labor union relationship detection
   - False positive filtering

### Smart Filtering

- **Government Exclusions**: Automatically excludes "City of", "County of", college, and university entities
- **Union Normalization**: Removes noise phrases like "international", "local", "committee"
- **Business Logic**: Handles slash notation and corporate structures
- **Threshold Filtering**: 85% default similarity requirement

## Architecture

### Core Components

- **ConflictAnalyzer**: Main orchestration and workflow management
- **FuzzyMatcher**: Multi-algorithm similarity calculation  
- **ClaudeValidator**: AI-powered false positive filtering
- **EntityNormalizer**: Smart entity name standardization
- **ConflictDataProcessor**: CSV loading and data validation
- **ConflictReportGenerator**: Multi-format report generation

### Design Principles

- **Dependency Injection**: Clean separation of concerns
- **Type Safety**: Comprehensive type annotations throughout
- **Error Handling**: Robust error recovery and logging
- **Configuration**: Centralized settings management
- **Modularity**: Independent, testable components

## Validation Rules

### Government Employee Exemption
Contributors who are government, college, or university employees are automatically excluded from potential conflicts.

### Labor Union Analysis
Union contributors are matched against union beneficiaries using normalized entity names that remove organizational noise.

### Entity Identity Test
Potential conflicts require that beneficiary and contributor represent the same legal entity or have direct operational control.

## Performance Considerations

- **Parallel Processing**: Optimized for multiple simultaneous operations
- **Memory Efficiency**: Streaming CSV processing for large datasets
- **API Rate Limiting**: Respectful Claude API usage with retry logic
- **Caching**: Entity normalization results cached for efficiency

## Troubleshooting

### Common Issues

**API Key Errors:**
```
Error: Anthropic API key not found
Solution: Add ANTHROPIC_API_KEY to your .env file
```

**CSV Format Errors:**
```
Error: Required column 'Beneficiary' not found
Solution: Verify CSV has all required columns with correct names
```

**Memory Issues:**
```
Error: Out of memory processing large files
Solution: Process files in smaller chunks or increase available memory
```

### Getting Help

1. **Check Logs**: Review console output for specific error messages
2. **Validate Data**: Ensure CSV files have required columns and proper formatting
3. **Test API**: Use `--test-api` flag to verify Claude connection
4. **Verbose Mode**: Use `--log-level DEBUG` for detailed diagnostic information

## License

This project is provided for educational and analytical purposes. Users are responsible for ensuring compliance with applicable laws and regulations when analyzing political data.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Ensure type safety and error handling
4. Add appropriate tests
5. Submit a pull request

For questions or issues, please review the troubleshooting section and check existing documentation before opening new issues. 