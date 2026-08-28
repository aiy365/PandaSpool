import re

with open('internal/store/store.go', 'r', encoding='utf-8') as f:
    content = f.read()

# Inject the migration for bambu_preset_id
migration = """	_, _ = s.DB.Exec("ALTER TABLE products ADD COLUMN bambu_preset_id TEXT NOT NULL DEFAULT ''")"""
if "ALTER TABLE products ADD COLUMN bambu_preset_id" not in content:
    content = content.replace("s.migrateSpools()", "s.migrateSpools()\n" + migration)

with open('internal/store/store.go', 'w', encoding='utf-8') as f:
    f.write(content)

# Update product.go
with open('internal/store/product.go', 'r', encoding='utf-8') as f:
    pcontent = f.read()

if "BambuPresetID" not in pcontent:
    pcontent = pcontent.replace('Material    string  `json:"material"`', 'Material    string  `json:"material"`\n\tBambuPresetID string `json:"bambu_preset_id"`')
    
    # ListProducts query update
    pcontent = pcontent.replace(
        'SELECT id, brand, product_line, material, notes, created_at FROM products',
        'SELECT id, brand, product_line, material, IFNULL(bambu_preset_id,""), notes, created_at FROM products'
    )
    pcontent = pcontent.replace(
        '&p.ID, &p.Brand, &p.ProductLine, &p.Material, &p.Notes, &p.CreatedAt',
        '&p.ID, &p.Brand, &p.ProductLine, &p.Material, &p.BambuPresetID, &p.Notes, &p.CreatedAt'
    )
    
    # SaveProduct query update
    pcontent = pcontent.replace(
        'INSERT INTO products (id, brand, product_line, material, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        'INSERT INTO products (id, brand, product_line, material, bambu_preset_id, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
    )
    pcontent = pcontent.replace(
        'p.ID, p.Brand, p.ProductLine, p.Material, p.Notes, p.CreatedAt',
        'p.ID, p.Brand, p.ProductLine, p.Material, p.BambuPresetID, p.Notes, p.CreatedAt'
    )
    pcontent = pcontent.replace(
        'UPDATE products SET brand=?, product_line=?, material=?, notes=? WHERE id=?',
        'UPDATE products SET brand=?, product_line=?, material=?, bambu_preset_id=?, notes=? WHERE id=?'
    )
    pcontent = pcontent.replace(
        'p.Brand, p.ProductLine, p.Material, p.Notes, p.ID',
        'p.Brand, p.ProductLine, p.Material, p.BambuPresetID, p.Notes, p.ID'
    )

with open('internal/store/product.go', 'w', encoding='utf-8') as f:
    f.write(pcontent)
print("Updated store.go and product.go")
