-- Migration: Add whatsapp_phone_number_id for multi-tenant support
-- Date: 2026-01-27
-- Description: Adds phone_number_id column to identify tenants by WhatsApp Business API phone number

-- Step 1: Add the column
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS whatsapp_phone_number_id VARCHAR(50);

-- Step 2: Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_clientes_whatsapp_phone_number_id ON clientes(whatsapp_phone_number_id);

-- Step 3: Verify the changes
SELECT id, nome, whatsapp_numero, whatsapp_phone_number_id FROM clientes;

-- Example: Update a specific client with their phone_number_id from Meta
-- UPDATE clientes
-- SET whatsapp_phone_number_id = '989612447561309'  -- Replace with actual value from .env WHATSAPP_PHONE_ID
-- WHERE id = 1;  -- Replace with actual client ID
