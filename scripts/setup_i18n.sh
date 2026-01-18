#!/bin/bash
# Script để setup i18n cho Flask app

echo "🌐 Setting up i18n for Flask app..."

# Create translations directory
mkdir -p translations

# Extract strings from code
echo "📝 Extracting strings from code..."
pybabel extract -F babel.cfg -k _ -o messages.pot .

# Initialize translations for each language
echo "📚 Initializing translations..."
pybabel init -i messages.pot -d translations -l en  # English (default)
pybabel init -i messages.pot -d translations -l da  # Danish
pybabel init -i messages.pot -d translations -l kl  # Greenlandic

echo "✅ Translation files created!"
echo ""
echo "Next steps:"
echo "1. Edit translations/*/LC_MESSAGES/messages.po to add translations"
echo "2. Or run: python scripts/translate_strings.py (auto-translate with Google)"
echo "3. Compile: pybabel compile -d translations"
echo "4. Update translations: pybabel update -i messages.pot -d translations"

