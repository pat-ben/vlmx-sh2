# VLMX-SH2: Domain-Specific Language Shell

A natural language command-line interface for managing business entities with intuitive syntax and powerful automation capabilities.

## Overview

VLMX-SH2 is a domain-specific language (DSL) shell that provides a conversational command-line interface for creating and managing business entities like companies, metadata, and organizational structures. The system uses natural language parsing with fuzzy matching to interpret user commands and execute business operations.

**Key Features:**
- Natural language command parsing with fuzzy matching
- Dynamic command system that works with any entity-field combination
- Flexible syntax supporting key=value and simplified formats
- Entity-relationship modeling with automatic validation
- Contextual session management (system, organization, application levels)
- JSON-based persistence with automatic schema management
- Extensible word registry for custom vocabulary

## Quick Start

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd vlmx-sh2

# Install dependencies
uv sync

# Run the application
uv run vlmx
```

### Basic Commands
```bash
# Create a company folder with JSON files + fill organization JSON + change context
create company XX legal=SA currency=USD

# Add a vision to the brand table
add brand vision=This_is_a_test

# Delete the vision
delete brand vision

# Open wizard for filling entity data interactively
fill brand

# List records with filtering for multi-cardinality entities
list offering key="Premium Service"

# Navigate one level up
cd ..

# Go to organization context
cd [company_name]
```

## Architecture Overview

VLMX-SH2 follows a layered architecture that separates concerns between parsing, validation, execution, and persistence:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│     Parser       │───▶│    Commands     │
│   (Natural      │    │   - Tokenizer    │    │   - Registry    │
│    Language)    │    │   - Word Recog.  │    │   - Validation  │
└─────────────────┘    │   - Value Extr.  │    │   - Matching    │
                       └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│     Storage     │◀───│    Handlers      │◀───│   Word Registry │
│   (JSON Files)  │    │   - Bus. Logic   │    │   - Vocabulary  │
│                 │    │   - Validation   │    │   - Entity Maps │
└─────────────────┘    │   - Transform.   │    └─────────────────┘
                       └──────────────────┘
```

## Core Concepts

### 1. UI Components

**Modal Screens**:
- **FormWizardScreen**: Interactive form-based data entry with validation
- **DynamicEntityScreen**: Split-screen interface for multi-record entity management

**Widgets**:
- **FormWizard**: Configurable form widget with field validation and pre-filled values
- **DynamicEntityManager**: Split-view widget combining searchable record lists with editing forms
- **RecordPicker**: Selection widget for choosing records from lists
- **CommandBlock**: Terminal-style command input and output blocks

### 2. Entities and Database Models

Entities represent real-world business objects and map directly to database tables:

```python
class CompanyEntity(DatabaseModel):
    name: str                    # Company name
    legal: Legal                 # Legal entity type (SA, LLC, INC)
    type: TypeOrg               # Organization type (company, fund)
    currency: Currency          # Operating currency (EUR, USD, GBP)
    unit: Unit                  # Financial units (thousands, millions)
    closing: int                # Fiscal year end month
    incorporation: Optional[date] # Date of incorporation
    # ... additional fields
```

**Entity Hierarchy:**
- **CompanyEntity**: Core company information
- **MetadataEntity**: Key-value extension data
- **BrandEntity**: Brand identity (vision, mission, values)
- **OfferingEntity**: Product/service offerings
- **TargetEntity**: Market segments and audiences
- **ValuesEntity**: Core company values
- **AddressEntity**: Company address information
- **NewsEntity**: Company news and announcements
- **CompetitorsEntity**: Competitor analysis data

### 2. Word Registry System

The word registry defines the vocabulary that users can use in commands. Each word has a specific type and relationship to database entities:

#### Word Types

**ActionWord**: Commands/verbs
```python
ActionWord(
    id="create",
    description="Create a new entity",
    action_category=ActionCategory.CRUD,
    crud_operation=CRUDOperation.CREATE,
    standalone=False
)
```

**EntityWord**: Business objects  
```python
EntityWord(
    id="company",
    description="A business entity",
    entity_model=CompanyEntity  # Links to database model
)
```

**FieldWord**: Entity properties
```python
FieldWord(
    id="currency", 
    description="Operating currency",
    entity_models=[CompanyEntity]  # Can belong to multiple entities
)
```

### 3. Command System

VLMX-SH2 supports both static and dynamic commands:

#### Static Commands
Commands with fixed syntax rules:
```python
@register_command(
    command_id="create_company",
    description="Create a new company entity",
    required_words={"create", "company"},      # Must be present
    optional_words={"entity", "currency"},     # Can be omitted
    context=ContextLevel.SYS                   # Required context level
)
async def create_company_handler(parse_result, context):
    # Implementation here
```

#### Dynamic Commands
Flexible commands that work with any valid entity-field combination:
```python
@register_command(
    command_id="add_dynamic",
    description="Add/set field values to any entity",
    required_words={"add"},                   # Only action word required
    optional_words=set(),                     # Empty for dynamic commands
    context=ContextLevel.ORG,
    is_dynamic=True                           # Enables dynamic behavior
)
async def add_dynamic_handler(parse_result, context):
    # Works with: add brand vision=..., add metadata key=..., etc.
```

#### Command Workflow

1. **Registration**: Commands register via decorators + explicit initialization
2. **Parsing**: User input tokenized and matched to words
3. **Validation**: Check required words and syntax rules (with dynamic validation for flexible commands)
4. **Execution**: Handler function called with parsed data
5. **Response**: Results formatted and displayed

### 4. Natural Language Parser

The parser converts user input into structured commands through multiple stages:

#### Tokenization
```python
# Input: "create company ACME entity=SA currency=EUR"
# Tokens: ["create", "company", "ACME", "entity", "SA", "currency", "EUR"]
```

#### Word Recognition
- Exact matching for known vocabulary
- Fuzzy matching with suggestions for typos
- Alias and abbreviation support

#### Value Extraction
- **Schema values**: Company names, IDs (ACME, ACME-CORP)
- **Field values**: Properties and settings (SA, EUR, THOUSANDS)
- **Key=value pairs**: Modern syntax (entity=SA currency=EUR)

#### Command Matching
- Find commands that accept the provided word combination
- Rank by completeness and specificity
- Validate against syntax rules

### 5. Context Management

The system maintains hierarchical execution contexts:

- **SYS (System)**: Global operations, company creation
- **ORG (Organization)**: Company-specific operations  
- **APP (Application)**: Plugin and tool-specific operations

```python
context = Context(level=0)                    # SYS level
context = Context(level=1, company="ACME")    # ORG level  
context = Context(level=2, plugin="reports")  # APP level
```

### 6. Storage Layer

JSON-based persistence with automatic file management:

```python
# Creates: ./companies.json
storage_result = create_company(entity_dict, context)

# File structure:
[
  {
    "name": "ACME",
    "legal": "SA", 
    "currency": "EUR",
    "created_at": "2025-01-15T10:30:00"
  }
]
```

## Developer Workflow

### Adding New Commands

#### Static Commands
1. **Define the vocabulary** in `dsl/words.py`:
```python
ActionWord(id="update", description="Update existing entity", ...)
```

2. **Create the command** in `handlers/crud.py`:
```python
@register_command(
    command_id="update_company",
    required_words={"update", "company"},
    optional_words={"legal", "currency"}
)
async def update_company_handler(parse_result, context):
    # Implementation
```

3. **Test the command**:
```bash
update company ACME legal=LLC
```

#### Dynamic Commands
For flexible commands that work with any entity-field combination:

1. **Create the dynamic command**:
```python
@register_command(
    command_id="process_dynamic",
    description="Process any entity with fields",
    required_words={"process"},
    optional_words=set(),
    is_dynamic=True,
    context=ContextLevel.ORG
)
async def process_dynamic_handler(parse_result, context):
    # Works with any valid entity-field combination from word registry
```

2. **Test with any entity-field combination**:
```bash
process brand vision=New_Vision
process metadata category=Technology
process organization name=NewName
```

### Adding New Entity Types

1. **Create the entity model** in `models/schema/company.py`:
```python
class ProjectEntity(DatabaseModel):
    name: str
    company_id: int
    status: ProjectStatus
```

2. **Add entity word** in `words.py`:
```python
EntityWord(
    id="project",
    description="Project management entity",
    entity_model=ProjectEntity
)
```

3. **Create handlers** for CRUD operations

### Dynamic Command Examples

The new dynamic command system provides powerful flexibility:

```bash
# Dynamic entity operations - works with any entity-field combination
add brand vision=This_is_our_vision
add metadata stage=GROWTH sector=AI
add company legal=LLC
add offering key=Premium_Service value=Enterprise_solutions

# Update any existing fields
update brand mission=Change_the_world
update company currency=EUR
update metadata stage=MATURE

# Show entity data or specific fields
show brand                    # Shows all brand data
show company name currency   # Shows only name and currency
show metadata                # Shows all metadata

# Interactive wizard for filling data
fill brand                   # Opens form wizard for brand entity
fill offering               # Opens split-screen manager for offerings

# List multi-cardinality entities with filtering
list offering               # Shows all offerings
list target key=Primary     # Filter targets by key
list news category=FUNDING  # Filter news by category

# Delete/clear specific fields
delete brand vision          # Sets vision to null
delete metadata stage       # Sets stage to null

# Navigation commands
cd ..                       # Go up one level
cd ACME                    # Enter company context
```

## File Structure

```
src/vlmx_sh2/
├── __init__.py              # Package initialization
├── main.py                  # Application entry point
├── constants.py             # System constants
├── dsl/                     # Domain-specific language components
│   ├── words.py            # Word registry and vocabulary
│   └── macros.py           # Command macros
├── models/                  # Data models
│   ├── context.py          # Session management
│   ├── results.py          # Result formatting
│   ├── words.py            # Word type definitions
│   ├── parser/             # Parser-related models
│   │   ├── enums.py        # Parser enums
│   │   ├── filter.py       # Filter models
│   │   ├── parse_result.py # Parse result models
│   │   ├── parsed_command.py # Parsed command models
│   │   ├── recognized_token.py # Token recognition
│   │   └── token.py        # Token definitions
│   └── schema/             # Database schema models
│       ├── base.py         # Base schema classes
│       ├── company.py      # Company entity models
│       ├── enums.py        # Schema enums
│       └── fund.py         # Fund entity models
├── parser/                  # Natural language parser
│   ├── parser.py           # Main parser logic
│   ├── tokenizer.py        # Text tokenization
│   ├── recognizer.py       # Word recognition
│   ├── filter.py           # Filter parsing
│   ├── suggestions.py      # Suggestion engine
│   └── utils.py            # Parser utilities
├── handlers/                # Command implementations
│   ├── crud.py             # CRUD operations
│   ├── navigation.py       # Navigation commands
│   ├── wizard.py           # Wizard commands
│   └── utils.py            # Handler utilities
├── storage/                 # Data persistence layer
│   ├── database.py         # Database operations
│   ├── mappings.py         # Data mappings
│   └── filters.py          # Data filtering
├── ui/                      # User interface components
│   ├── app.py              # Main Textual application
│   ├── results.py          # Result formatting
│   ├── screens/            # Screen components
│   │   ├── main/           # Main screen
│   │   │   └── main_screen.py
│   │   └── modal/          # Modal screens
│   │       ├── dynamic_entity_screen.py  # Split-screen entity manager
│   │       └── form_wizard_screen.py     # Form wizard modal
│   ├── widgets/            # UI widgets
│   │   ├── command_block.py          # Command input blocks
│   │   ├── dynamic_entity_manager.py # Split-view entity manager
│   │   ├── form_wizard.py            # Interactive form wizard
│   │   └── record_picker.py          # Record selection widget
│   └── styles/             # CSS styling
└── enums/                   # Shared enumerations
    └── forms.py            # Form-related enums
```

## Configuration

### Adding Custom Vocabulary

Extend the word registry by adding new entries to `dsl/words.py`:

```python
WORDS.extend([
    ActionWord(id="analyze", description="Analyze entity data", ...),
    EntityWord(id="report", description="Report entity", entity_model=ReportEntity),
    FieldWord(id="format", description="Report format", entity_models=[ReportEntity])
])
```

### Custom Storage Backends

Implement the storage interface for different backends:

```python
def create_entity(entity_type: str, data: dict, context: Context) -> dict:
    # Custom implementation (database, API, etc.)
    return {"success": True, "message": "Entity created"}
```

## Testing

```bash
# Run the application
uv run vlmx

# Run with development mode
uv run textual run --dev src.vlmx_sh2.ui.app:VLMX

# Test individual components
uv run python -c "
from src.vlmx_sh2.parser import VLMXParser
parser = VLMXParser()
result = parser.parse('create company TEST legal=SA')
print(result.best_command.command_id)
"
```

## Contributing

1. Follow the existing architectural patterns
2. Add comprehensive docstrings to new modules
3. Register new words in the central registry
4. Use the command decorator system for new commands
5. Write tests for new functionality
6. Update this documentation for significant changes

## License

[Your License Here]