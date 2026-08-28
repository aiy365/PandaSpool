import re

with open('internal/server/spool_api.go', 'r', encoding='utf-8') as f:
    content = f.read()

# Add getInitial and import for pinyin
if '"github.com/mozillazg/go-pinyin"' not in content:
    content = content.replace('"strings"', '"strings"\n\t"github.com/mozillazg/go-pinyin"')

initial_func = """
func getInitial(s string) string {
	s = strings.TrimSpace(s)
	if len(s) == 0 {
		return "x"
	}
	r := []rune(s)[0]
	if (r >= 'A' && r <= 'Z') || (r >= 'a' && r <= 'z') {
		return strings.ToLower(string(r))
	}
	dict := map[rune]string{
		'拓': "t", '竹': "z", '易': "y", '生': "s", '兰': "l", '博': "b", '创': "c", '想': "x", '闪': "s", '铸': "z",
		'红': "h", '粉': "f", '蓝': "l", '绿': "l", '黄': "h", '黑': "h", '白': "b", '紫': "z", '棕': "z", '透': "t",
		'金': "j", '银': "y", '灰': "h", '彩': "c", '特': "t", '橙': "c", '青': "q", '木': "m", '自': "z", '明': "m",
		'亚': "y", '哑': "y", '亮': "l", '丝': "s", '夜': "y", '大': "d", '筒': "t", '无': "w",
	}
	if val, ok := dict[r]; ok {
		return val
	}
	a := pinyin.NewArgs()
	a.Style = pinyin.FirstLetter
	py := pinyin.Pinyin(string(r), a)
	if len(py) > 0 && len(py[0]) > 0 {
		return strings.ToLower(py[0][0])
	}
	return "x"
}
"""
if "func getInitial" not in content:
    content = content.replace("func getBambuFilamentID", initial_func + "\nfunc getBambuFilamentID")

# Modify spoolIntake inside loop:
# Replace: shortCode, _ := s.st.NextShortCode()
# With: prefix := getInitial(targetProduct.Brand) + getInitial(targetColor.Name)
#       shortCode, _ := s.st.NextShortCode(prefix)
old_shortcode = "shortCode, _ := s.st.NextShortCode()"
new_shortcode = """prefix := getInitial(targetProduct.Brand) + getInitial(targetColor.Name)
		shortCode, _ := s.st.NextShortCode(prefix)"""
content = content.replace(old_shortcode, new_shortcode)

# Add Note to CloudFilament
old_cloud = """		f := bambu.CloudFilament{
			FilamentID:   filamentID,
			FilamentName: filamentName,
			Color:        "FF0000FF", // fallback color
			NetWeight:    1000,
		}"""
new_cloud = """		f := bambu.CloudFilament{
			FilamentID:   filamentID,
			FilamentName: filamentName,
			Color:        "FF0000FF", // fallback color
			NetWeight:    1000,
			Note:         fmt.Sprintf("%s (%s) - PrintPilot Sync", shortCode, targetColor.Name),
		}"""
content = content.replace(old_cloud, new_cloud)

with open('internal/server/spool_api.go', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated internal/server/spool_api.go")
