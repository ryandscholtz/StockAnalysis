#!/bin/bash
# Bash script to switch LLM providers
# Usage: ./switch_llm_provider.sh llama
#        ./switch_llm_provider.sh anthropic
#        ./switch_llm_provider.sh openai

if [ $# -eq 0 ]; then
    echo "Usage: $0 [llama|anthropic|openai]"
    exit 1
fi

PROVIDER=$1

if [[ ! "$PROVIDER" =~ ^(llama|anthropic|openai)$ ]]; then
    echo "Error: Provider must be one of: llama, anthropic, openai"
    exit 1
fi

ENV_FILE=".env"

# Create .env if it doesn't exist
if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
fi

# Update or add LLM_PROVIDER
if grep -q "^LLM_PROVIDER=" "$ENV_FILE"; then
    sed -i.bak "s/^LLM_PROVIDER=.*/LLM_PROVIDER=$PROVIDER/" "$ENV_FILE"
    rm -f "$ENV_FILE.bak"
else
    echo "LLM_PROVIDER=$PROVIDER" >> "$ENV_FILE"
fi

# Add provider-specific config if needed
if [ "$PROVIDER" = "llama" ]; then
    if ! grep -q "^LLAMA_API_URL=" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# Llama/Ollama Configuration" >> "$ENV_FILE"
        echo "LLAMA_API_URL=http://localhost:11434" >> "$ENV_FILE"
        echo "LLAMA_MODEL=llava:7b" >> "$ENV_FILE"
    fi
elif [ "$PROVIDER" = "anthropic" ]; then
    if ! grep -q "^ANTHROPIC_API_KEY=" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# Anthropic Configuration" >> "$ENV_FILE"
        echo "# ANTHROPIC_API_KEY=your_key_here" >> "$ENV_FILE"
    fi
elif [ "$PROVIDER" = "openai" ]; then
    if ! grep -q "^OPENAI_API_KEY=" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# OpenAI Configuration" >> "$ENV_FILE"
        echo "# OPENAI_API_KEY=your_key_here" >> "$ENV_FILE"
    fi
fi

echo ""
echo "✓ Switched LLM provider to: $PROVIDER"
echo ""
echo "Current configuration:"
grep -E "LLM_PROVIDER|LLAMA_|ANTHROPIC_|OPENAI_" "$ENV_FILE" | sed 's/^/  /'
echo ""
echo "Note: Restart your backend server for changes to take effect."

