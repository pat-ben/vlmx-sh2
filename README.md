# VLMX-SH2: Domain-Specific Language Shell

A modern natural language command-line interface for managing business entities with sophisticated parsing, dynamic word generation, and contextual session management.

## Overview

VLMX-SH2 is a domain-specific language (DSL) shell that provides an intuitive command-line interface for creating and managing business entities like companies, organizations, and their relationships. The system uses advanced natural language parsing with dynamic vocabulary generation to interpret user commands and execute business operations.

**Key Features:**
- 7-stage natural language processing pipeline with sophisticated parsing
- Dynamic word registry auto-generated from Pydantic database schemas
- Cumulative context system (SYS → ORG → APP) with contextual command availability
- Modern Textual-based UI with form wizards and split-screen entity management
- Type-safe Pydantic v2 integration with automatic validation
- Unified command execution pipeline supporting both text and wizard inputs
- SQL-inspired semantics with comprehensive error handling and suggestions

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
# Create a company database
create company ACME legal=SA currency=USD

# Navigate to company context  
cd acme/

# Add brand information
add brand vision="Transform the industry" mission="Excellence in innovation"

# Show entity data
show brand                    # All brand fields
show organization name legal  # Specific fields only

# Interactive form wizard
fill brand                   # Opens guided form

# List multi-record entities
show offering                # Shows all offerings
show news category=FUNDING   # Filtered results

# Navigate between contexts
cd ..                        # Up one level
cd ~/                        # Root/SYS level
cd acme/neco/               # APP context (future)
```

## Architecture Overview

VLMX-SH2 follows a sophisticated layered architecture with a 7-stage parsing pipeline:

```
┌─────────────────┐    ┌──────────────────────────────┐    ┌─────────────────┐
│   User Input    │───▶│       Parser (Stages 0-6)   │───▶│ CommandBuilder  │
│  (Natural Lang) │    │ 0: Normalizer (macros)      │    │   (Stage 7)     │
└─────────────────┘    │ 1: Tokenizer (text→tokens)  │    │ - ParsedCommand │
                       │ 2: Classifier (token types)  │    │ - Validation    │
                       │ 3: Recognizer (DSL words)   │    └─────────────────┘
                       │ 4: Interpreter (context)     │            │
                       │ 5: Splitter (cmd/filter)    │            ▼
                       │ 6: Filter (AST generation)   │    ┌─────────────────┐
                       └──────────────────────────────┘    │     Router      │
                                │                          │ - Handler Match │
                                ▼                          │ - Dispatch      │
┌─────────────────┐    ┌──────────────────┐              └─────────────────┘
│     Storage     │◀───│    Handlers      │◀──────────────────────┘
│   (JSON Files)  │    │ - CRUD Operations│
│                 │    │ - Navigation     │    ┌─────────────────┐
└─────────────────┘    │ - Wizards        │    │  Word Registry  │
                       │ - Apps (Tools)   │───▶│ - Dynamic Gen   │
                       └──────────────────┘    │ - Schema Maps   │
                                               └─────────────────┘
```

## Core Concepts

### 1. Context Management System

VLMX-SH2 uses a cumulative three-level context hierarchy:

```python
# SYS Level (0): System operations - Schema only
~ $ create company ACME legal=SA

# ORG Level (1): Organization operations - Schema + Module + Entity + Field  
~/acme $ add brand vision="Our vision"

# APP Level (2): Application operations - All word types (future)
~/acme/neco $ apply view parameters=...
```

**Cumulative Model**: Higher levels inherit all capabilities from lower levels:
- **SYS**: Schema words only (`company`, `fund`)
- **ORG**: SYS + Module + Entity + Field words (`branding`, `organization`, `vision`)
- **APP**: ORG + View + Tool words (`neco`, `dcf`) *(future)*

### 2. Dynamic Word Registry System

The system auto-generates vocabulary from Pydantic database schemas, eliminating duplication:

#### Word Types

**ActionWord** - Commands/Verbs (manually defined):
```python
ActionWord(
    id="create",
    description="Create a new schema or structure", 
    handler=create_handler,
    crud_operation=CRUDOperation.CREATE
)
```

**SchemaWord** - Database Schemas (auto-generated):
```python
# Generated from database schema classes
SchemaWord(
    id="company",
    description="A business organization database",
    schema_class=CompanyDatabase,
    aliases=["co"]
)
```

**EntityWord** - Business Objects (auto-generated):
```python
# Generated from Pydantic models in schemas
EntityWord(
    id="organization", 
    description="Core company information",
    entity_model=OrganizationEntity,
    cardinality=Cardinality.SINGLE,
    aliases=["org", "o"]
)
```

**FieldWord** - Entity Attributes (auto-generated):
```python
# Generated from Pydantic model fields
FieldWord(
    id="vision",
    description="Company vision statement", 
    entity_models=[BrandEntity],
    field_type=str
)
```

**ModuleWord** - Entity Groupings (auto-generated):
```python
# Generated by grouping entities by module
ModuleWord(
    id="branding",
    description="Brand identity entities",
    entities=["brand", "values"]
)
```

**ViewWord/ToolWord** - Apps (manually defined, future):
```python
ViewWord(id="neco", description="NECO reporting view", app_type="view")
ToolWord(id="dcf", description="DCF calculation tool", app_type="tool")
```

### 3. Entity System

Entities are Pydantic models that map directly to JSON storage:

```python
class OrganizationEntity(DatabaseModel):
    """Core company information (single record)"""
    name: str                    # Company name
    legal: Legal                 # Legal entity type (SA, LLC, INC)
    currency: Currency          # Operating currency (EUR, USD, GBP)
    unit: Unit                  # Financial units (thousands, millions)
    stage: Optional[Stage]      # Business stage (STARTUP, GROWTH, etc.)
    sector: Optional[Sector]    # Industry sector
    incorporation: Optional[date] # Date of incorporation

class BrandEntity(DatabaseModel):
    """Brand identity information (single record)"""  
    vision: Optional[str]       # Company vision
    mission: Optional[str]      # Company mission
    promise: Optional[str]      # Brand promise
    positioning: Optional[str]  # Market positioning

class OfferingEntity(DatabaseModel):
    """Product/service offerings (multiple records)"""
    key: str                    # Offering identifier
    value: str                  # Offering description
    category: Optional[str]     # Offering category
```

**Entity Hierarchy (CompanyDatabase schema):**
- **Core Module**: `organization`, `metadata`, `address`
- **Branding Module**: `brand`, `values`  
- **Market Module**: `offering`, `target`, `news`, `competitors`

### 4. Command Execution Pipeline

The system uses a unified 8-stage pipeline:

#### Stages 0-6: Text Parsing
1. **Normalizer**: Macro expansion and preprocessing
2. **Tokenizer**: Text splitting and boundary detection  
3. **Classifier**: Token type classification (WORD, VALUE, OPERATOR)
4. **Recognizer**: DSL word recognition with fuzzy matching
5. **Interpreter**: Context-aware token interpretation
6. **Splitter**: Command/filter separation
7. **Filter**: Filter AST generation

#### Stage 7: Command Building
- **CommandBuilder**: Constructs ParsedCommand from tokens or wizard data
- Unified interface for both text commands and form submissions

#### Command Handlers
- **CRUD Handlers**: `create`, `add`, `show`, `delete`, `drop`, `reset`
- **Navigation**: `cd` for context switching
- **Interactive**: `fill` for form wizards
- **Apps**: `apply` (views), `run` (tools) *(future)*

### 5. Modern UI Components

Built with Textual framework for responsive terminal interfaces:

**Screens:**
- **MainScreen**: Primary command interface with terminal-style interaction
- **FormWizardScreen**: Modal form interface for guided data entry
- **DynamicEntityScreen**: Split-screen entity management *(future)*

**Widgets:**
- **CommandBlock**: Terminal-style command input/output
- **FormWizard**: Interactive form with validation and pre-filled values
- **RecordPicker**: Selection interface for multi-record entities
- **DynamicEntityManager**: Split-view for record lists and editing

### 6. Storage and Persistence

JSON-based storage with automatic schema management:

```python
# File structure: ./companies/acme/
├── company.json             # Root organization entity (named after table_name)
├── brand.json
├── address.json
├── metadata.json
├── values.json
├── offering.json           # Multi-record entities (arrays)
├── target.json
├── news.json
└── competitors.json
```

**Features:**
- Automatic file creation and management
- Schema validation via Pydantic models
- Cardinality-aware storage (single vs multiple records)
- Atomic operations with error handling

## Command Reference

### Core Commands

#### Schema Operations (SYS context)
```bash
create company <name> [legal=<type>] [currency=<curr>] ...
drop company <name>
show company [<name>]
```

#### Entity Operations (ORG context)
```bash
# Add/update field values
add <entity> <field>=<value> [<field>=<value>] ...
add brand vision="Transform the industry" mission="Excellence"
add organization legal=LLC currency=USD
add offering key="Premium" value="Enterprise solutions"

# Show entity data  
show <entity>                    # All fields
show <entity> <field> [<field>]  # Specific fields
show brand                       # All brand information
show organization name legal     # Just name and legal type
show offering                    # All offerings (multi-record)

# Delete field values
delete <entity> <field> [<field>] ...
delete brand vision              # Clear vision field
delete offering key="Premium"    # Delete specific offering

# Interactive forms
fill <entity>                    # Open form wizard
fill brand                      # Guided brand information entry

# Structure operations
drop <entity>                    # Delete entire entity
reset <entity>                   # Reset to defaults
```

#### Navigation
```bash
cd ~                    # System level
cd <company>/           # Organization level
cd <company>/<app>/     # Application level (future)
cd ..                   # Up one level
```

#### Module Operations (ORG context)
```bash
show <module>           # Show all entities in module
show branding          # Shows brand + values entities
show market            # Shows offering + target + news + competitors
```

### Advanced Features

#### Field Value Syntax
```bash
# Key=value pairs (recommended)
add organization legal=SA currency=EUR unit=MILLIONS

# Space-separated values (legacy)
add organization SA EUR MILLIONS

# Quoted values for spaces
add brand vision="Our vision for the future"
add offering key="Premium Service" value="Enterprise solutions"
```

#### Entity Filtering *(future)*
```bash
show offering category=Premium
show news category=FUNDING date>2024-01-01
list target key="Primary Market"
```

#### Module Groupings
- **core**: `organization`, `metadata`, `address`
- **branding**: `brand`, `values`
- **market**: `offering`, `target`, `news`, `competitors`

## Developer Guide

### Adding New Entity Types

1. **Define the Pydantic model** in `schemas/company.py`:
```python
class ProjectEntity(DatabaseModel):
    """Project management entity"""
    name: str
    status: ProjectStatus = ProjectStatus.PLANNING
    budget: Optional[Decimal] = None
    company_id: int  # Foreign key (auto-added)
```

2. **Add to database schema**:
```python
class CompanyDatabase(DatabaseSchema):
    organization: OrganizationEntity
    project: ProjectEntity  # Auto-generates EntityWord and FieldWords
    # ... other entities
```

3. **Test the new entity**:
```bash
add project name="New Project" status=ACTIVE budget=50000
show project
fill project  # Interactive form
```

### Adding New Actions

1. **Create handler** in `handlers/`:
```python
async def analyze_handler(parsed_command: ParsedCommand, context: Context) -> HandlerResult:
    # Implementation here
    return CommandResult(success=True, message="Analysis complete")
```

2. **Register action** in `dsl/actions.py`:
```python
ActionWord(
    id="analyze",
    description="Analyze entity data",
    handler=analyze_handler,
    action_category=ActionCategory.ANALYSIS
)
```

3. **Test the command**:
```bash
analyze organization  # Uses new handler
```

### Custom Word Types

For manual word definitions, add to appropriate generators in `dsl/generator.py`:

```python
def generate_view_words():
    return {
        "neco": ViewWord(
            id="neco",
            description="NECO investment reporting view",
            app_type="view",
            entities=["organization", "offering"]
        )
    }
```

## File Structure

```
src/vlmx_sh2/
├── __init__.py                 # Package initialization
├── main.py                     # CLI entry point  
├── core/                       # Command execution pipeline
│   ├── builder.py             # Stage 7: ParsedCommand construction
│   ├── executor.py            # Main execution orchestrator
│   └── router.py              # Handler routing and dispatch
├── models/                     # Data models and structures
│   ├── context.py             # Session and navigation context
│   ├── words.py               # Word type definitions (ActionWord, etc.)
│   ├── parser/                # Parser-related models
│   │   ├── command.py         # ParsedCommand model
│   │   ├── interpretation.py  # InterpretedToken model
│   │   ├── recognition.py     # RecognizedToken model  
│   │   ├── filtering.py       # Filter AST models
│   │   └── tokenization.py    # Token models
│   ├── responses/             # Handler response models
│   │   ├── results.py         # CommandResult, ErrorResult
│   │   └── __init__.py        # HandlerResult union
│   └── validation.py          # ValidationContext
├── parser/                     # Natural language processing (Stages 0-6)
│   ├── parser.py              # Main parser orchestrator
│   ├── normalizer.py          # Stage 0: Macro expansion
│   ├── tokenizer.py           # Stage 1: Text tokenization
│   ├── classifier.py          # Stage 2: Token classification
│   ├── recognizer.py          # Stage 3: DSL word recognition
│   ├── interpreter.py         # Stage 4: Context interpretation
│   ├── splitter.py            # Stage 5: Command/filter splitting
│   └── filter.py              # Stage 6: Filter AST generation
├── dsl/                        # Domain-specific language
│   ├── registry.py            # Central word registry
│   ├── actions.py             # ActionWord definitions
│   ├── generator.py           # Auto-generation from schemas
│   └── words.py               # Word re-exports
├── handlers/                   # Command execution handlers
│   ├── crud.py                # CRUD operations
│   ├── navigation.py          # Context navigation (cd)
│   ├── wizard.py              # Form wizard (fill)
│   ├── apps.py                # View/tool handlers (apply, run)
│   └── utils.py               # Shared utilities
├── schemas/                    # Database schema definitions
│   ├── base.py                # Base schema classes
│   └── company.py             # Company entity models
├── storage/                    # Data persistence layer
│   ├── database.py            # File operations
│   └── mappings.py            # Entity-file mappings
├── enums/                      # Enumerations and constants
│   ├── core.py                # Core enums (ContextLevel, etc.)
│   ├── context_rules.py       # Context validation rules
│   └── forms.py               # Form-related enums
├── ui/                         # Textual-based user interface
│   ├── app.py                 # Main Textual application
│   ├── screens/               # Screen components
│   │   ├── main/              # Main command interface
│   │   └── modal/             # Modal screens (forms, managers)
│   ├── widgets/               # Reusable UI widgets
│   └── styles/                # CSS styling
├── diagnostics/                # Validation and error reporting
│   ├── validation.py          # ValidationContext
│   └── errors.py              # Error handling utilities
└── utils/                      # Utility functions
    └── context_helpers.py     # Context manipulation helpers
```

## Configuration and Customization

### Environment Setup
```bash
# Development mode with debugging
uv run textual run --dev src.vlmx_sh2.ui.app:VLMX

# Direct parser testing
uv run python -c "
from src.vlmx_sh2.core.executor import CommandExecutor
from src.vlmx_sh2.models.context import Context
executor = CommandExecutor()
result = executor.execute('create company TEST legal=SA', Context())
print(result)
"
```

### Custom Schema Integration
```python
# Add new database schema
class FundDatabase(DatabaseSchema):
    fund_info: FundInfoEntity
    investors: InvestorEntity
    portfolio: PortfolioEntity

# Register in dsl/registry.py
SCHEMAS = [
    CompanyDatabase,
    FundDatabase  # Automatically generates words
]
```

## Testing

```bash
# Run the application
uv run vlmx

# Development mode with live reload
uv run textual run --dev src.vlmx_sh2.ui.app:VLMX

# Test parsing pipeline
PYTHONPATH=src uv run python -c "
from vlmx_sh2.parser.parser import Parser
from vlmx_sh2.models.context import Context
context = Context()
result = Parser.parse('add brand vision=test', context)
print('Valid:', result.is_valid)
"

# Test word generation
PYTHONPATH=src uv run python -c "
from vlmx_sh2.dsl.registry import ENTITY_WORDS, FIELD_WORDS
print('Entities:', list(ENTITY_WORDS.keys()))
print('Fields:', list(FIELD_WORDS.keys())[:10])
"
```

## Contributing

1. **Architecture**: Follow the 8-stage pipeline design pattern
2. **Models**: Use Pydantic v2 with proper type annotations
3. **Words**: Prefer auto-generation over manual definitions
4. **Handlers**: Implement proper validation and error handling
5. **Testing**: Validate both parsing and execution stages
6. **Documentation**: Update README for significant architectural changes

## License

[Your License Here]