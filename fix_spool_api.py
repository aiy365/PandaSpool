import re

with open('internal/server/spool_api.go', 'r', encoding='utf-8') as f:
    content = f.read()

old_loop = """		bambuCloudID, err := adapter.CreateFilament(f)
		if err != nil {
			http.Error(w, fmt.Sprintf("failed to create cloud filament: %v", err), http.StatusInternalServerError)
			return
		}

		sp := store.Spool{
			ColorID:           req.ColorID,
			ShortCode:         shortCode,
			BambuCloudID:      bambuCloudID,
			BambuFilamentID:   filamentID,
			BambuFilamentName: filamentName,
			BambuRegion:       cfg.Bambu.Region,
			NetWeightG:        1000,
			Status:            "unopened",
		}

		_, err = s.st.SaveSpool(sp)
		if err != nil {
			http.Error(w, fmt.Sprintf("failed to save local spool: %v", err), http.StatusInternalServerError)
			return
		}
	}

	s.spoolsList(w, r)
}"""

new_loop = """		bambuCloudID, err := adapter.CreateFilament(f)
		if err != nil {
			if i > 0 {
				break // partial success, just return what we have
			}
			http.Error(w, fmt.Sprintf("failed to create cloud filament: %v", err), http.StatusInternalServerError)
			return
		}

		sp := store.Spool{
			ColorID:           req.ColorID,
			ShortCode:         shortCode,
			BambuCloudID:      bambuCloudID,
			BambuFilamentID:   filamentID,
			BambuFilamentName: filamentName,
			BambuRegion:       cfg.Bambu.Region,
			NetWeightG:        1000,
			Status:            "unopened",
		}

		_, err = s.st.SaveSpool(sp)
		if err != nil {
			if i > 0 {
				break
			}
			http.Error(w, fmt.Sprintf("failed to save local spool: %v", err), http.StatusInternalServerError)
			return
		}
	}

	s.spoolsList(w, r)
}"""

content = content.replace(old_loop, new_loop)

with open('internal/server/spool_api.go', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated spool_api.go loop.")
