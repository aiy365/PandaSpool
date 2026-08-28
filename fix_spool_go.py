import re

with open('internal/store/spool.go', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace NextShortCode signature
content = content.replace('func (s *Store) NextShortCode() (string, error) {', 'func (s *Store) NextShortCode(prefix string) (string, error) {')

# Modify the query
old_query = "`SELECT short_code FROM spools WHERE short_code LIKE 'PP-%' ORDER BY CAST(SUBSTR(short_code, 4) AS INTEGER) DESC LIMIT 1`"
new_query = "fmt.Sprintf(`SELECT short_code FROM spools WHERE short_code LIKE '%s%%' ORDER BY CAST(SUBSTR(short_code, %d) AS INTEGER) DESC LIMIT 1`, prefix, len(prefix)+1)"
content = content.replace(f"err := s.DB.QueryRow({old_query}).Scan(&maxCode)", f"err := s.DB.QueryRow({new_query}).Scan(&maxCode)")

# Modify the formatting logic
old_parse = """	if maxCode.Valid && maxCode.String != "" {
		_, _ = fmt.Sscanf(maxCode.String, "PP-%d", &seq)
	}
	seq++
	return fmt.Sprintf("PP-%03d", seq), nil"""
new_parse = """	if maxCode.Valid && maxCode.String != "" {
		_, _ = fmt.Sscanf(maxCode.String, prefix+"%d", &seq)
	}
	seq++
	return fmt.Sprintf("%s%03d", prefix, seq), nil"""
content = content.replace(old_parse, new_parse)

# Update SaveSpool calls to NextShortCode
content = content.replace('sp.ShortCode, _ = s.NextShortCode()', 'sp.ShortCode, _ = s.NextShortCode("PP-")')

with open('internal/store/spool.go', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated internal/store/spool.go")
