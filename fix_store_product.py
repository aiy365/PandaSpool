import re

with open('internal/store/store.go', 'r', encoding='utf-8') as f:
    content = f.read()

if "BambuPresetID string `json:\"bambu_preset_id\"`" not in content:
    content = content.replace('Material    string  `json:"material"`', 'Material    string  `json:"material"`\n\tBambuPresetID string `json:"bambu_preset_id"`')
    
    # ListProducts query update
    content = content.replace(
        'SELECT id, brand, product_line, material, notes, created_at FROM products',
        'SELECT id, brand, product_line, material, IFNULL(bambu_preset_id,""), notes, created_at FROM products'
    )
    content = content.replace(
        '&p.ID, &p.Brand, &p.ProductLine, &p.Material, &p.Notes, &p.CreatedAt',
        '&p.ID, &p.Brand, &p.ProductLine, &p.Material, &p.BambuPresetID, &p.Notes, &p.CreatedAt'
    )
    content = content.replace(
        'SELECT id, brand, product_line, material, notes, created_at FROM products WHERE id=?',
        'SELECT id, brand, product_line, material, IFNULL(bambu_preset_id,""), notes, created_at FROM products WHERE id=?'
    )
    
    # SaveProduct query update
    content = content.replace(
        'INSERT INTO products (id, brand, product_line, material, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        'INSERT INTO products (id, brand, product_line, material, bambu_preset_id, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)'
    )
    content = content.replace(
        'p.ID, p.Brand, p.ProductLine, p.Material, p.Notes, p.CreatedAt',
        'p.ID, p.Brand, p.ProductLine, p.Material, p.BambuPresetID, p.Notes, p.CreatedAt'
    )
    content = content.replace(
        'UPDATE products SET brand=?, product_line=?, material=?, notes=? WHERE id=?',
        'UPDATE products SET brand=?, product_line=?, material=?, bambu_preset_id=?, notes=? WHERE id=?'
    )
    content = content.replace(
        'p.Brand, p.ProductLine, p.Material, p.Notes, p.ID',
        'p.Brand, p.ProductLine, p.Material, p.BambuPresetID, p.Notes, p.ID'
    )

with open('internal/store/store.go', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated store.go (Product struct and queries)")
