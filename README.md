# VLMX-SH2: Domain-Specific Language Shell

A natural language command-line interface for managing business entities with intuitive syntax and powerful automation capabilities.

## Overview

VLMX-SH2 is a domain-specific language (DSL) shell that provides a conversational command-line interface for creating and managing business entities like companies, metadata, and organizational structures. The system uses natural language parsing with fuzzy matching to interpret user commands and execute business operations.

**Key Features:**
- Natural language command parsing with fuzzy matching
- Flexible syntax supporting both flag-based and simplified formats
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
uv run python -m src.vlmx_sh2.layout
```

### Basic Commands
```bash
# Create a company with simplified syntax
create company ACME entity=SA currency=EUR

# Or use traditional flag syntax  
create company ACME --entity=SA --currency=EUR

# Delete a company
delete company ACME
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

### 1. Entities and Database Models

Entities represent real-world business objects and map directly to database tables:

```python
class OrganizationEntity(DatabaseModel):
    name: str                    # Company name
    entity: Entity              # Legal entity type (SA, LLC, INC)
    type: Type                  # Organization type (company, fund)
    currency: Currency          # Operating currency (EUR, USD, GBP)
    unit: Unit                  # Financial units (thousands, millions)
    # ... additional fields
```

**Entity Hierarchy:**
- **OrganizationEntity**: Core company information
- **MetadataEntity**: Key-value extension data
- **BrandEntity**: Brand identity (vision, mission, values)
- **OfferingEntity**: Product/service offerings
- **TargetEntity**: Market segments and audiences
- **ValueEntity**: Core company values

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
    requires_entity=True
)
```

**EntityWord**: Business objects  
```python
EntityWord(
    id="company",
    description="A business entity",
    entity_model=OrganizationEntity  # Links to database model
)
```

**AttributeWord**: Entity properties
```python
AttributeWord(
    id="currency", 
    description="Operating currency",
    entity_models=[OrganizationEntity]  # Can belong to multiple entities
)
```

**ModifierWord**: Behavioral modifiers
```python
ModifierWord(
    id="holding",
    description="Holding company modifier",
    applies_to=["company"]
)
```

### 3. Command System

Commands define the syntax rules for valid user input by specifying which words are required or optional:

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

#### Command Workflow

1. **Registration**: Commands register via decorators + explicit initialization
2. **Parsing**: User input tokenized and matched to words
3. **Validation**: Check required words and syntax rules
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
- **Entity values**: Company names, IDs (ACME, ACME-CORP)
- **Attribute values**: Properties and settings (SA, EUR, THOUSANDS)
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
    "entity": "SA", 
    "currency": "EUR",
    "created_at": "2025-01-15T10:30:00"
  }
]
```

## Developer Workflow

### Adding New Commands

1. **Define the vocabulary** in `words.py`:
```python
ActionWord(id="update", description="Update existing entity", ...)
```

2. **Create the command** in `handlers.py`:
```python
@register_command(
    command_id="update_company",
    required_words={"update", "company"},
    optional_words={"entity", "currency"}
)
async def update_company_handler(parse_result, context):
    # Implementation

# Add to register_all_commands() verification
def register_all_commands():
    expected_commands = ["create_company", "delete_company", "update_company"]  # Add new command
    # ... rest of function
```

3. **Test the command**:
```bash
update company ACME entity=LLC
```

### Adding New Entity Types

1. **Create the entity model** in `entities.py`:
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
    entity_model=ProjectEntity
)
```

3. **Create handlers** for CRUD operations

### Extending Syntax

The parser supports flexible syntax patterns:

```bash
# Simple format
create company ACME entity=SA

# Traditional flags  
create company ACME --entity=SA --currency=EUR

# Future: Natural language
create a new SA company called ACME using EUR currency
```

## File Structure

```
src/vlmx_sh2/
├── __init__.py         # Package initialization
├── enums.py           # Type definitions and constants  
├── entities.py        # Database entity models
├── words.py           # Word registry and vocabulary
├── commands.py        # Command system and registry
├── parser.py          # Natural language parser
├── handlers.py        # Command implementations
├── results.py         # Result formatting
├── storage.py         # Data persistence layer
├── context.py         # Session management
├── syntax.py          # Composition rules
├── databases.py       # Schema definitions
└── layout.py          # Textual UI application
```

## Configuration

### Adding Custom Vocabulary

Extend the word registry by adding new entries to `words.py`:

```python
WORDS.extend([
    ActionWord(id="analyze", description="Analyze entity data", ...),
    EntityWord(id="report", entity_model=ReportEntity),
    AttributeWord(id="format", entity_models=[ReportEntity])
])
```

### Custom Storage Backends

Implement the storage interface for different backends:

```python
def create_entity(entity_dict: dict, context: Context) -> dict:
    # Custom implementation (database, API, etc.)
    return {"success": True, "id": "generated_id"}
```

## Testing

```bash
# Run with development mode
uv run textual run --dev src.vlmx_sh2.layout

# Test individual components
uv run python -c "
from src.vlmx_sh2.parser import VLMXParser
parser = VLMXParser()
result = parser.parse('create company TEST entity=SA')
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