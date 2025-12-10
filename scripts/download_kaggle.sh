!/bin/bash
# Download LogHub Apache Log Data from Kaggle

set -e

echo "========================================="
echo "📥 Downloading LogHub Apache Log Data"
echo "========================================="

# Check for Kaggle credentials
if [ ! -f ~/.kaggle/kaggle.json ]; then
  echo "❌ Kaggle credentials not found!"
  echo ""
  echo "Please follow these steps:"
  echo "1. Go to https://www.kaggle.com/settings"
  echo "2. Scroll to 'API' section"
  echo "3. Click 'Create New API Token'"
  echo "4. Save kaggle.json to ~/.kaggle/"
  echo "5. Run: chmod 600 ~/.kaggle/kaggle.json"
  exit 1
fi

# Create raw directory
mkdir -p raw

# Download dataset
echo "Downloading dataset..."
kaggle datasets download -d omduggineni/loghub-apache-log-data

# Unzip
echo "Extracting..."
unzip -o loghub-apache-log-data.zip -d raw/

# Cleanup
rm loghub-apache-log-data.zip

echo ""
echo "✅ Dataset downloaded to: raw/"
echo ""
echo "Next steps:"
echo "  1. python scripts/preprocess.py --input raw/Apache.log --output cleaned.log"
echo "  2. python src/siem_pipeline.py --input cleaned.log --workers 4 --rate 500 ..."