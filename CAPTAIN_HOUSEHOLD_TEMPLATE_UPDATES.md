# Captain Module Household Template Updates

## Overview

This document provides instructions to update `captain_householdList.html` and `captain_moreHousehold.html` to match the secretary module's implementation with PDF generation capabilities.

---

## ✅ COMPLETED CHANGES

### 1. PDF Views Added (`captain_module/views.py`)

- ✅ Added `generate_household_list_pdf()` function
- ✅ Added `generate_household_detail_pdf()` function
- Both functions match the secretary module implementation

### 2. URL Routes Added (`captain_module/urls.py`)

- ✅ Added `household_list/pdf/` route
- ✅ Added `household/<int:household_id>/pdf/` route

---

## 📝 MANUAL TEMPLATE UPDATES REQUIRED

### captain_householdList.html

#### Change 1: Update Search and Filter Section (Lines ~38-110)

**Replace the old control form** with this enhanced version:

```html
<div class="px-6 py-6">
  <h2 class="text-lg font-semibold text-red-700 mb-4">Household List</h2>

  <!-- Search + Filters -->
  <div class="mb-5 flex items-center gap-2">
    <form id="searchForm" method="GET" class="flex items-center gap-2 grow">
      <div class="relative w-full sm:w-[420px]">
        <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3.5">
          <svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/>
          </svg>
        </div>
        <input type="text" placeholder="Search by household number, head, or address..."
               name="query" id="queryInput" value="{{ query|default:'' }}"
               class="w-full rounded-xl border-gray-300 pl-10 pr-4 text-sm shadow-sm focus:border-red-500 focus:ring-red-500">
      </div>
      <input type="hidden" name="quarter_id" value="{{ quarter_id }}" />
      <input type="hidden" name="status" value="{{ status }}" />
      <input type="hidden" name="sitio_id" value="{{ sitio_id }}" />
      <input type="hidden" name="limit" value="{{ limit }}" />
      <input type="hidden" name="page" id="pageField" value="{{ page }}">
      <button class="rounded-xl bg-rose-600 text-white px-4 py-2.5 text-sm font-semibold shadow hover:bg-rose-700 inline-flex items-center gap-2">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"/>
        </svg>
        Search
      </button>
    </form>

    <!-- Filters dropdown -->
    <details class="relative">
      <summary tabindex="0" role="button" class="inline-flex items-center gap-2 rounded-xl bg-white text-gray-700 px-4 py-2.5 text-sm font-semibold shadow border border-gray-300 hover:bg-gray-50 cursor-pointer select-none">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L15 13.414V19a1 1 0 01-1.447.894l-4-2A1 1 0 019 17V13.414L3.293 6.707A1 1 0 013 6V4z"/>
        </svg>
        Filters
        {% if status_chip or sitio_chip %}
          <span class="ml-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-rose-600 text-xs font-bold text-white">
            {% if status_chip and sitio_chip %}2{% elif status_chip or sitio_chip %}1{% endif %}
          </span>
        {% endif %}
      </summary>
      <div class="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded-xl shadow-lg z-10 p-4">
        <form method="GET" class="space-y-4">
          <input type="hidden" name="query" value="{{ query|default:'' }}" />
          <input type="hidden" name="page" value="1" />

          <!-- Quarter -->
          <div>
            <label for="quarter_id_filter" class="block text-sm font-medium text-gray-700 mb-1.5">Quarter</label>
            <select id="quarter_id_filter" name="quarter_id"
                    class="w-full rounded-xl border-gray-300 text-sm shadow-sm focus:border-red-500 focus:ring-red-500">
              <option value="">— All Quarters —</option>
              {% for q in quarter %}
                <option value="{{ q.quarter_id }}" {% if q.quarter_id == quarter_id %}selected{% endif %}>
                  {{ q.quarter_name }}
                </option>
              {% endfor %}
            </select>
          </div>

          <!-- Sitio -->
          <div>
            <label for="sitio_id_filter" class="block text-sm font-medium text-gray-700 mb-1.5">Sitio</label>
            <select id="sitio_id_filter" name="sitio_id"
                    class="w-full rounded-xl border-gray-300 text-sm shadow-sm focus:border-red-500 focus:ring-red-500">
              <option value="">— All Sitios —</option>
              {% for s in sitio %}
                <option value="{{ s.sitio_id }}" {% if sitio_id == s.sitio_id %}selected{% endif %}>
                  {{ s.sitio_name }}
                </option>
              {% endfor %}
            </select>
          </div>

          <!-- Status -->
          <div>
            <label for="status_filter" class="block text-sm font-medium text-gray-700 mb-1.5">Status</label>
            <select id="status_filter" name="status"
                    class="w-full rounded-xl border-gray-300 text-sm shadow-sm focus:border-red-500 focus:ring-red-500">
              <option value="all">— All Statuses —</option>
              <option value="active" {% if status == "active" %}selected{% endif %}>Active</option>
              <option value="inactive" {% if status == "inactive" %}selected{% endif %}>Inactive</option>
            </select>
          </div>

          <!-- Limit -->
          <div>
            <label for="limit_filter" class="block text-sm font-medium text-gray-700 mb-1.5">Rows per page</label>
            <select id="limit_filter" name="limit"
                    class="w-full rounded-xl border-gray-300 text-sm shadow-sm focus:border-red-500 focus:ring-red-500">
              {% for n in limit_options %}
                <option value="{{ n }}" {% if n == limit %}selected{% endif %}>{{ n }}</option>
              {% endfor %}
            </select>
          </div>

          <div class="flex gap-2 pt-2">
            <button type="submit" class="flex-1 rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-rose-700">
              Apply Filters
            </button>
            <a href="{% url 'captain_module:captain_householdList' %}?quarter_id={{ quarter_id }}"
               class="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-2 text-center text-sm font-semibold text-gray-700 shadow hover:bg-gray-50">
              Clear All
            </a>
          </div>
        </form>
      </div>
    </details>
  </div>

  <!-- Active filter chips -->
  {% if status_chip or sitio_chip %}
    <div class="mb-3 flex items-center gap-2 text-sm">
      <span class="text-gray-600">Active:</span>
      {% if status_chip %}
        <span class="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
          {{ status_chip }}
          <a href="{{ status_clear_url }}" class="text-gray-400 hover:text-gray-600">×</a>
        </span>
      {% endif %}
      {% if sitio_chip %}
        <span class="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
          {{ sitio_chip }}
          <a href="{{ sitio_clear_url }}" class="text-gray-400 hover:text-gray-600">×</a>
        </span>
      {% endif %}
      <a href="{{ clear_all_url }}" class="ml-2 inline-flex items-center gap-1 text-gray-700 hover:text-rose-700">
        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        Clear all
      </a>
    </div>
  {% endif %}
```

#### Change 2: Add PDF Generation Button (Before table, after filters)

```html
<!-- Table -->
<div class="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
  <!-- Generate PDF Button -->
  {% if results|length > 0 and not results.0.household_id == 0 %}
  <div class="mb-4 flex justify-end">
    <form
      method="GET"
      action="{% url 'captain_module:generate_household_list_pdf' %}"
      target="_blank"
    >
      <input type="hidden" name="query" value="{{ query|default:'' }}" />
      <input type="hidden" name="status" value="{{ status }}" />
      <input type="hidden" name="sitio_id" value="{{ sitio_id }}" />
      <input type="hidden" name="quarter_id" value="{{ quarter_id }}" />
      <button
        type="submit"
        class="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow hover:bg-red-700"
      >
        <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fill-rule="evenodd"
            d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z"
            clip-rule="evenodd"
          />
        </svg>
        Generate PDF
      </button>
    </form>
  </div>
  {% endif %}

  <table class="w-full text-left border-collapse"></table>
</div>
```

#### Change 3: Update Table Headers

**Replace** the table header row with:

```html
<thead>
  <tr class="bg-gradient-to-r from-gray-50 to-gray-100 text-gray-700">
    <th class="py-3 px-4 border-b font-semibold">Household No.</th>
    <th class="py-3 px-4 border-b font-semibold">Household Head</th>
    <th class="py-3 px-4 border-b font-semibold">Full Address</th>
    <th class="py-3 px-4 border-b font-semibold">Active Status</th>
    <th class="py-3 px-4 border-b font-semibold text-center">Action</th>
  </tr>
</thead>
```

**Note:** Remove the "Household ID" column to match secretary module.

#### Change 4: Update JavaScript

**Replace** the JavaScript section with:

```html
<script>
  // Debounce
  function debounce(fn, ms) {
    let t;
    return (...a) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...a), ms);
    };
  }

  const searchForm = document.getElementById("searchForm");
  const pageField = document.getElementById("pageField");
  const queryInput = document.getElementById("queryInput");

  // Search input debounce
  if (queryInput && searchForm) {
    const SEARCH_DEBOUNCE_MS = 1000;
    queryInput.addEventListener(
      "input",
      debounce(() => {
        pageField.value = 1;
        searchForm.requestSubmit();
      }, SEARCH_DEBOUNCE_MS)
    );
  }

  (function () {
    const modal = document.getElementById("visitModal");
    const backdrop = modal?.firstElementChild;
    const visitHid = document.getElementById("visit_hid");
    const visitVisited = document.getElementById("visit_visited");
    const visitHead = document.getElementById("visit_head");
    const visitNumber = document.getElementById("visit_number");
    const visitAlready = document.getElementById("visit_already");
    const btnCancel = document.getElementById("visitCancel");

    function openModal() {
      modal.classList.remove("hidden");
      modal.classList.add("flex");
      document.documentElement.classList.add("overflow-y-hidden");
    }
    function closeModal() {
      modal.classList.add("hidden");
      modal.classList.remove("flex");
      document.documentElement.classList.remove("overflow-y-hidden");
    }

    // Open + populate only for non-visited buttons (current quarter only)
    document.querySelectorAll(".openVisitModal").forEach((btn) => {
      btn.addEventListener("click", () => {
        visitHid.value = btn.dataset.hid || "";
        visitVisited.value = "False";
        visitHead.textContent = btn.dataset.head || "";
        visitNumber.textContent = btn.dataset.number || "";

        visitAlready.classList.add("hidden");
        openModal();
      });
    });

    // Close handlers
    btnCancel?.addEventListener("click", closeModal);
    backdrop?.addEventListener("click", (e) => {
      if (e.target === backdrop) closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !modal.classList.contains("hidden"))
        closeModal();
    });
  })();
</script>
```

---

### captain_moreHousehold.html

**Since this file is very large (2393 lines), you can copy it from secretary module:**

1. Copy `secretary_module/templates/secretary_module/moreHousehold.html`
2. Paste as `captain_module/templates/captain_module/captain_moreHousehold.html`
3. **Find and Replace ALL instances:**
   - `base_sec.html` → `base_captain.html`
   - `secretary_module:` → `captain_module:` (in all URL tags)
   - Specifically replace:
     - `{% url 'secretary_module:sec_householdView' %}` → `{% url 'captain_module:captain_householdView' %}`
     - All other secretary_module URL references

**Key Features to Verify:**

- ✅ Quarter selector at top
- ✅ Household card with all details
- ✅ Family cards with expandable details
- ✅ Member cards within families
- ✅ Modals for updates (Update Family, Update Member, etc.)
- ✅ Read-only mode when viewing past quarters or inactive households
- ✅ Visit button logic
- ✅ Generate Profile PDF button for each family

---

## 🧪 TESTING CHECKLIST

After making these changes, test the following:

### Household List Page

- [ ] Search functionality works (debounced)
- [ ] Filter dropdown shows/hides properly
- [ ] Active filter chips display correctly
- [ ] Status filter (Active/Inactive) works
- [ ] Sitio filter works
- [ ] Quarter filter works
- [ ] Limit (rows per page) works
- [ ] Pagination works
- [ ] **Generate PDF button appears** when households exist
- [ ] **PDF generation works** with all filters applied
- [ ] Visit button logic correct (green/gray, enabled/disabled)

### Household Detail Page

- [ ] Quarter selector works
- [ ] Household information displays correctly
- [ ] Family cards expand/collapse
- [ ] Member cards display within families
- [ ] Update buttons work (when in current quarter + active)
- [ ] Update buttons disabled (when past quarter or inactive)
- [ ] **Generate Profile PDF button** appears for each family
- [ ] **PDF generation works** for family profiles
- [ ] All modals open/close properly
- [ ] Read-only mode enforced correctly

---

## 📁 FILES MODIFIED

✅ **Completed:**

1. `captain_module/views.py` - Added PDF generation functions
2. `captain_module/urls.py` - Added PDF routes

📝 **Manual Updates Required:** 3. `captain_module/templates/captain_module/captain_householdList.html` 4. `captain_module/templates/captain_module/captain_moreHousehold.html`

---

## 💡 QUICK REFERENCE

**PDF URL Names:**

- List PDF: `captain_module:generate_household_list_pdf`
- Detail PDF: `captain_module:generate_household_detail_pdf`

**Required Context Variables (ensure views pass these):**

- `status_chip`, `sitio_chip`
- `status_clear_url`, `sitio_clear_url`, `clear_all_url`
- `quarter_id`, `results`, `quarter`
- `limit_options`, `page`, `has_prev`, `has_next`

---

## ❓ NEED HELP?

If you encounter issues:

1. Check console for JavaScript errors
2. Verify all URL names match between templates and urls.py
3. Ensure PDF generator classes are imported correctly
4. Check that context variables are passed from views
5. Compare with secretary module's working implementation

---

**Generated:** 2025-11-28
**Status:** Backend Complete, Templates Need Manual Update
