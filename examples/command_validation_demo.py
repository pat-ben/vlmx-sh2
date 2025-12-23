#!/usr/bin/env python3
"""
CommandWords Validation Demo

This script demonstrates how the new CommandWords validation system works:

1. Validates that word IDs exist in the word registry
2. Prevents overlap between required and optional words
3. Provides type-organized helper methods
4. Shows proper error handling for invalid configurations

Run this script to see validation in action!
"""

import os
import sys

# Add the src directory to the path so we can import vlmx_sh2 modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pydantic import ValidationError

from vlmx_sh2.commands import CommandWords
from vlmx_sh2.enums import WordType
from vlmx_sh2.words import get_all_words, get_words_by_type


def print_available_words():
    """Print all available words organized by type"""
    print("=== Available Words in Registry ===")

    for word_type in WordType:
        words = get_words_by_type(word_type)
        print(f"\n{word_type.value.upper()} Words:")
        for word_id, word in words.items():
            aliases_str = (
                f" (aliases: {', '.join(word.aliases)})" if word.aliases else ""
            )
            print(f"  - {word_id}: {word.description}{aliases_str}")


def demo_valid_configurations():
    """Demonstrate valid CommandWords configurations"""
    print("\n=== Valid CommandWords Configurations ===")

    # Example 1: Basic valid configuration
    try:
        cmd1 = CommandWords(
            required_words={"create", "company"}, optional_words={"entity", "currency"}
        )
        print(
            f"✅ Valid: {cmd1.required_words} (required) + {cmd1.optional_words} (optional)"
        )
        print(f"   All words: {cmd1.get_all_words()}")
        print(f"   Action words: {cmd1.get_words_by_type(WordType.ACTION)}")
        print(f"   Entity words: {cmd1.get_words_by_type(WordType.ENTITY)}")
        print(f"   Attribute words: {cmd1.get_words_by_type(WordType.ATTRIBUTE)}")

    except ValidationError as e:
        print(f"❌ Unexpected error: {e}")

    # Example 2: Using the type-organized helper
    try:
        cmd2 = CommandWords.from_word_types(
            required_actions={"delete"},
            required_entities={"company"},
            optional_attributes={"entity"},
        )
        print(
            f"✅ Valid (using helper): required={cmd2.required_words}, optional={cmd2.optional_words}"
        )

    except ValidationError as e:
        print(f"❌ Unexpected error: {e}")


def demo_invalid_word_ids():
    """Demonstrate validation errors for invalid word IDs"""
    print("\n=== Invalid Word ID Validation ===")

    # Example 1: Non-existent word ID
    try:
        CommandWords(
            required_words={"create", "nonexistent_word"}, optional_words={"currency"}
        )
        print("❌ Should have failed - nonexistent word was allowed!")
    except ValidationError as e:
        print(f"✅ Correctly caught invalid word ID: {e}")

    # Example 2: Typo in word ID
    try:
        CommandWords(
            required_words={"create", "compnay"},  # typo: should be "company"
            optional_words={"currency"},
        )
        print("❌ Should have failed - typo was allowed!")
    except ValidationError as e:
        print(f"✅ Correctly caught typo: {e}")


def demo_overlap_validation():
    """Demonstrate validation for required/optional word overlap"""
    print("\n=== Required/Optional Overlap Validation ===")

    try:
        CommandWords(
            required_words={"create", "company"},
            optional_words={"company", "currency"},  # "company" appears in both!
        )
        print("❌ Should have failed - overlap was allowed!")
    except ValidationError as e:
        print(f"✅ Correctly caught overlap: {e}")


def demo_word_queries():
    """Demonstrate querying methods"""
    print("\n=== CommandWords Query Methods ===")

    cmd = CommandWords(
        required_words={"create", "company"}, optional_words={"entity", "currency"}
    )

    print(f"All words: {cmd.get_all_words()}")
    print(f"Is 'create' allowed? {cmd.is_word_allowed('create')}")
    print(f"Is 'delete' allowed? {cmd.is_word_allowed('delete')}")
    print(f"Is 'currency' allowed? {cmd.is_word_allowed('currency')}")

    print(f"'create' is: {cmd.get_requirement_type('create')}")
    print(f"'entity' is: {cmd.get_requirement_type('entity')}")

    try:
        print(f"'delete' is: {cmd.get_requirement_type('delete')}")
    except ValueError as e:
        print(f"✅ Correctly caught query for unknown word: {e}")


def main():
    """Run all demonstration examples"""
    print("CommandWords Validation System Demo")
    print("=" * 50)

    try:
        print_available_words()
        demo_valid_configurations()
        demo_invalid_word_ids()
        demo_overlap_validation()
        demo_word_queries()

        print("\n" + "=" * 50)
        print("Demo completed successfully! 🎉")
        print("\nKey Benefits:")
        print("• Validates word IDs exist in registry at creation time")
        print("• Prevents configuration errors early")
        print("• Provides clear error messages")
        print("• Organizes words by type for better readability")
        print("• Prevents typos and references to non-existent words")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
