# Szczegółowy opis kodu (PL)

Dokument opisuje **każdy plik Python** oraz **każdą funkcję/metodę** wraz z zakresem linii. Dzięki numerom linii można przejść przez kod krok po kroku nawet bez znajomości projektu.

## Jak czytać „linijka po linijce”
- Otwórz wskazany plik i przejdź do podanego zakresu `Lx-Ly`.
- W pierwszych liniach funkcji zwykle jest walidacja wejścia i przygotowanie danych.
- Środkowa część realizuje logikę biznesową (parsowanie, filtrowanie, agregacje, aktualizacja GUI).
- Końcowe linie zwracają wynik, zapisują dane do cache lub odświeżają widok.
- Dla dużych metod (np. `MainWindowHandlers`) czytaj po blokach nazwanych komentarzami i wywołaniami pomocniczych metod.

## Plik: `hfm_analyzer/__init__.py`
- **Rola pliku:** Plik inicjalizacyjny pakietu.
- **Elementy kodu:** brak jawnych funkcji/klas; plik zawiera głównie stałe, importy lub inicjalizację pakietu.

## Plik: `hfm_analyzer/app.py`
- **Rola pliku:** Uruchamianie aplikacji Qt: konfiguracja ścieżek, stylu i głównego okna.
- **Elementy kodu (z zakresem linii):**
  - `Funkcja `ensure_base_path()`` — linie **19-54**. Funkcja/metoda realizuje krok związany z: „ensure base path”.
  - `Funkcja `apply_fusion_palette()`` — linie **57-72**. Funkcja/metoda realizuje krok związany z: „apply fusion palette”.
  - `Funkcja `_icon_search_paths()`` — linie **75-114**. Funkcja/metoda realizuje krok związany z: „icon search paths”.
  - `Funkcja `_load_app_icon()`` — linie **117-124**. Funkcja/metoda realizuje krok związany z: „load app icon”.
  - `Funkcja `main()`` — linie **127-161**. Funkcja/metoda realizuje krok związany z: „main”.

## Plik: `hfm_analyzer/constants.py`
- **Rola pliku:** Stałe aplikacji i domyślne parametry.
- **Elementy kodu (z zakresem linii):**
  - `Funkcja `default_cycle_time_sec()`` — linie **16-21**. Funkcja/metoda realizuje krok związany z: „default cycle time sec”.

## Plik: `hfm_analyzer/data_labels.py`
- **Rola pliku:** Słowniki/etykiety mapujące nazwy techniczne na opisy dla UI.
- **Elementy kodu:** brak jawnych funkcji/klas; plik zawiera głównie stałe, importy lub inicjalizację pakietu.

## Plik: `hfm_analyzer/gui/__init__.py`
- **Rola pliku:** Plik inicjalizacyjny pakietu.
- **Elementy kodu:** brak jawnych funkcji/klas; plik zawiera głównie stałe, importy lub inicjalizację pakietu.

## Plik: `hfm_analyzer/gui/dialogs.py`
- **Rola pliku:** Okna dialogowe ustawień oraz sprawdzania dostępności zasobów i cache.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `_PathCheckWorker`` — linie **36-45**. Klasa odpowiedzialna za obszar: „PathCheckWorker”.
  - `  - Metoda `_PathCheckWorker.__init__()`` — linie **39-41**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `_PathCheckWorker.run()`` — linie **43-45**. Funkcja/metoda realizuje krok związany z: „run”.
  - `Klasa `SettingsDialog`` — linie **47-396**. Klasa odpowiedzialna za obszar: „SettingsDialog”.
  - `  - Metoda `SettingsDialog.__init__()`` — linie **50-187**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `SettingsDialog._on_path_text_changed()`` — linie **189-192**. Funkcja/metoda realizuje krok związany z: „on path text changed”.
  - `  - Metoda `SettingsDialog._cycle_time_key()`` — linie **194-195**. Funkcja/metoda realizuje krok związany z: „cycle time key”.
  - `  - Metoda `SettingsDialog._cycle_time_for_line()`` — linie **197-199**. Funkcja/metoda realizuje krok związany z: „cycle time for line”.
  - `  - Metoda `SettingsDialog._on_line_id_changed()`` — linie **201-209**. Funkcja/metoda realizuje krok związany z: „on line id changed”.
  - `  - Metoda `SettingsDialog._apply_path()`` — linie **211-218**. Funkcja/metoda realizuje krok związany z: „apply path”.
  - `  - Metoda `SettingsDialog._set_path()`` — linie **220-225**. Funkcja/metoda realizuje krok związany z: „set path”.
  - `  - Metoda `SettingsDialog._browse()`` — linie **227-230**. Funkcja/metoda realizuje krok związany z: „browse”.
  - `  - Metoda `SettingsDialog._browse_cache_path()`` — linie **232-244**. Funkcja/metoda realizuje krok związany z: „browse cache path”.
  - `  - Metoda `SettingsDialog._default_cache_path()`` — linie **246-263**. Funkcja/metoda realizuje krok związany z: „default cache path”.
  - `  - Metoda `SettingsDialog._set_offline_preset()`` — linie **265-276**. Funkcja/metoda realizuje krok związany z: „set offline preset”.
  - `  - Metoda `SettingsDialog._on_persistent_toggled()`` — linie **278-288**. Funkcja/metoda realizuje krok związany z: „on persistent toggled”.
  - `  - Metoda `SettingsDialog._on_offline_toggled()`` — linie **290-302**. Funkcja/metoda realizuje krok związany z: „on offline toggled”.
  - `  - Metoda `SettingsDialog._clear_cache()`` — linie **304-335**. Funkcja/metoda realizuje krok związany z: „clear cache”.
  - `  - Metoda `SettingsDialog._accept()`` — linie **337-396**. Funkcja/metoda realizuje krok związany z: „accept”.
  - `Klasa `NetworkCheckDialog`` — linie **398-597**. Klasa odpowiedzialna za obszar: „NetworkCheckDialog”.
  - `  - Metoda `NetworkCheckDialog.__init__()`` — linie **401-465**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `NetworkCheckDialog._apply_styles()`` — linie **467-473**. Funkcja/metoda realizuje krok związany z: „apply styles”.
  - `  - Metoda `NetworkCheckDialog._update_label()`` — linie **475-477**. Funkcja/metoda realizuje krok związany z: „update label”.
  - `  - Metoda `NetworkCheckDialog._choose_path()`` — linie **479-482**. Funkcja/metoda realizuje krok związany z: „choose path”.
  - `  - Metoda `NetworkCheckDialog._set_path()`` — linie **484-497**. Funkcja/metoda realizuje krok związany z: „set path”.
  - `  - Metoda `NetworkCheckDialog._on_retry()`` — linie **499-500**. Funkcja/metoda realizuje krok związany z: „on retry”.
  - `  - Metoda `NetworkCheckDialog._set_controls_enabled()`` — linie **502-513**. Funkcja/metoda realizuje krok związany z: „set controls enabled”.
  - `  - Metoda `NetworkCheckDialog._start_path_check()`` — linie **515-536**. Funkcja/metoda realizuje krok związany z: „start path check”.
  - `  - Metoda `NetworkCheckDialog._on_path_check_finished()`` — linie **538-553**. Funkcja/metoda realizuje krok związany z: „on path check finished”.
  - `  - Metoda `NetworkCheckDialog._offline_cache_available()`` — linie **555-583**. Funkcja/metoda realizuje krok związany z: „offline cache available”.
  - `  - Metoda `NetworkCheckDialog._use_offline_cache()`` — linie **585-597**. Funkcja/metoda realizuje krok związany z: „use offline cache”.
  - `Klasa `CacheCheckDialog`` — linie **601-714**. Klasa odpowiedzialna za obszar: „CacheCheckDialog”.
  - `  - Metoda `CacheCheckDialog.__init__()`` — linie **604-651**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `CacheCheckDialog._apply_styles()`` — linie **653-659**. Funkcja/metoda realizuje krok związany z: „apply styles”.
  - `  - Metoda `CacheCheckDialog._update_label()`` — linie **661-665**. Funkcja/metoda realizuje krok związany z: „update label”.
  - `  - Metoda `CacheCheckDialog._cache_available()`` — linie **667-675**. Funkcja/metoda realizuje krok związany z: „cache available”.
  - `  - Metoda `CacheCheckDialog._on_retry()`` — linie **677-682**. Funkcja/metoda realizuje krok związany z: „on retry”.
  - `  - Metoda `CacheCheckDialog._choose_cache()`` — linie **684-707**. Funkcja/metoda realizuje krok związany z: „choose cache”.
  - `  - Metoda `CacheCheckDialog._use_online()`` — linie **709-714**. Funkcja/metoda realizuje krok związany z: „use online”.

## Plik: `hfm_analyzer/gui/handlers.py`
- **Rola pliku:** Największa warstwa logiki GUI: reakcje na zdarzenia, filtrowanie, render tabel i eksporty.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `MainWindowHandlers`` — linie **92-6177**. Klasa odpowiedzialna za obszar: „MainWindowHandlers”.
  - `  - Metoda `MainWindowHandlers.closeEvent()`` — linie **93-123**. Funkcja/metoda realizuje krok związany z: „closeEvent”.
  - `  - Metoda `MainWindowHandlers._fetch_param_snapshots()`` — linie **125-153**. Funkcja/metoda realizuje krok związany z: „fetch param snapshots”.
  - `  - Metoda `MainWindowHandlers._fetch_index_snapshots()`` — linie **155-183**. Funkcja/metoda realizuje krok związany z: „fetch index snapshots”.
  - `  - Metoda `MainWindowHandlers._fetch_struct_snapshots()`` — linie **185-218**. Funkcja/metoda realizuje krok związany z: „fetch struct snapshots”.
  - `  - Metoda `MainWindowHandlers._analysis_cache_filters()`` — linie **220-228**. Funkcja/metoda realizuje krok związany z: „analysis cache filters”.
  - `  - Metoda `MainWindowHandlers._current_analysis_range()`` — linie **230-238**. Funkcja/metoda realizuje krok związany z: „current analysis range”.
  - `  - Metoda `MainWindowHandlers._filter_intranet_rows_for_analysis()`` — linie **240-254**. Funkcja/metoda realizuje krok związany z: „filter intranet rows for analysis”.
  - `  - Metoda `MainWindowHandlers._dedup_intranet_rows()`` — linie **256-266**. Funkcja/metoda realizuje krok związany z: „dedup intranet rows”.
  - `  - Metoda `MainWindowHandlers._apply_styles()`` — linie **268-333**. Funkcja/metoda realizuje krok związany z: „apply styles”.
  - `  - Metoda `MainWindowHandlers._format_log_message()`` — linie **335-340**. Funkcja/metoda realizuje krok związany z: „format log message”.
  - `  - Metoda `MainWindowHandlers._append_log()`` — linie **342-347**. Funkcja/metoda realizuje krok związany z: „append log”.
  - `  - Metoda `MainWindowHandlers._log()`` — linie **349-354**. Funkcja/metoda realizuje krok związany z: „log”.
  - `  - Metoda `MainWindowHandlers._yield_ui()`` — linie **356-362**. Funkcja/metoda realizuje krok związany z: „yield ui”.
  - `  - Metoda `MainWindowHandlers._is_offline_cache_mode()`` — linie **364-368**. Funkcja/metoda realizuje krok związany z: „is offline cache mode”.
  - `  - Metoda `MainWindowHandlers._set_offline_cache_mode()`` — linie **370-374**. Funkcja/metoda realizuje krok związany z: „set offline cache mode”.
  - `  - Metoda `MainWindowHandlers._on_tree_color_metric_changed()`` — linie **376-380**. Funkcja/metoda realizuje krok związany z: „on tree color metric changed”.
  - `  - Metoda `MainWindowHandlers._cycle_time_sec_for_current_line()`` — linie **382-394**. Funkcja/metoda realizuje krok związany z: „cycle time sec for current line”.
  - `  - Metoda `MainWindowHandlers._line_presets()`` — linie **396-410**. Funkcja/metoda realizuje krok związany z: „line presets”.
  - `  - Metoda `MainWindowHandlers._refresh_line_selector()`` — linie **412-463**. Funkcja/metoda realizuje krok związany z: „refresh line selector”.
  - `  - Metoda `MainWindowHandlers._on_line_selector_changed()`` — linie **465-499**. Funkcja/metoda realizuje krok związany z: „on line selector changed”.
  - `  - Metoda `MainWindowHandlers._refresh_base_path_label()`` — linie **501-511**. Funkcja/metoda realizuje krok związany z: „refresh base path label”.
  - `  - Metoda `MainWindowHandlers._get_base_path()`` — linie **513-514**. Funkcja/metoda realizuje krok związany z: „get base path”.
  - `  - Metoda `MainWindowHandlers._default_persistent_cache_path()`` — linie **516-533**. Funkcja/metoda realizuje krok związany z: „default persistent cache path”.
  - `  - Metoda `MainWindowHandlers._create_runtime_cache()`` — linie **535-565**. Funkcja/metoda realizuje krok związany z: „create runtime cache”.
  - `  - Metoda `MainWindowHandlers._select_all()`` — linie **567-569**. Funkcja/metoda realizuje krok związany z: „select all”.
  - `  - Metoda `MainWindowHandlers._deselect_all()`` — linie **571-573**. Funkcja/metoda realizuje krok związany z: „deselect all”.
  - `  - Metoda `MainWindowHandlers._remember_default_date_bounds()`` — linie **575-582**. Funkcja/metoda realizuje krok związany z: „remember default date bounds”.
  - `  - Metoda `MainWindowHandlers._reset_date_bounds()`` — linie **584-594**. Funkcja/metoda realizuje krok związany z: „reset date bounds”.
  - `  - Metoda `MainWindowHandlers._apply_cache_date_bounds()`` — linie **596-631**. Funkcja/metoda realizuje krok związany z: „apply cache date bounds”.
  - `  - Metoda `MainWindowHandlers._populate_machines_from_cache()`` — linie **633-669**. Funkcja/metoda realizuje krok związany z: „populate machines from cache”.
  - `  - Metoda `MainWindowHandlers._populate_machines()`` — linie **671-704**. Funkcja/metoda realizuje krok związany z: „populate machines”.
  - `  - Metoda `MainWindowHandlers._browse_base_path()`` — linie **706-714**. Funkcja/metoda realizuje krok związany z: „browse base path”.
  - `  - Metoda `MainWindowHandlers._open_settings()`` — linie **716-745**. Funkcja/metoda realizuje krok związany z: „open settings”.
  - `  - Metoda `MainWindowHandlers._start_scan()`` — linie **747-779**. Funkcja/metoda realizuje krok związany z: „start scan”.
  - `  - Metoda `MainWindowHandlers._start_cache_only_analysis()`` — linie **781-844**. Funkcja/metoda realizuje krok związany z: „start cache only analysis”.
  - `  - Metoda `MainWindowHandlers._on_progress()`` — linie **846-871**. Funkcja/metoda realizuje krok związany z: „on progress”.
  - `  - Metoda `MainWindowHandlers._on_error()`` — linie **873-878**. Funkcja/metoda realizuje krok związany z: „on error”.
  - `  - Metoda `MainWindowHandlers._on_finished()`` — linie **880-906**. Funkcja/metoda realizuje krok związany z: „on finished”.
  - `  - Metoda `MainWindowHandlers._prepare_analysis_files()`` — linie **908-957**. Funkcja/metoda realizuje krok związany z: „prepare analysis files”.
  - `  - Metoda `MainWindowHandlers._find_previous_backup_file()`` — linie **959-1043**. Funkcja/metoda realizuje krok związany z: „find previous backup file”.
  - `  - Metoda `MainWindowHandlers._render_summary()`` — linie **1045-1499**. Funkcja/metoda realizuje krok związany z: „render summary”.
  - `  - Metoda `MainWindowHandlers._quality_rollup_by_machine()`` — linie **1501-1684**. Funkcja/metoda realizuje krok związany z: „quality rollup by machine”.
  - `  - Metoda `MainWindowHandlers._build_intranet_series()`` — linie **1686-1700**. Funkcja/metoda realizuje krok związany z: „build intranet series”.
  - `  - Metoda `MainWindowHandlers._load_intranet_from_cache()`` — linie **1702-1749**. Funkcja/metoda realizuje krok związany z: „load intranet from cache”.
  - `  - Metoda `MainWindowHandlers._start_intranet_fetch()`` — linie **1751-1872**. Funkcja/metoda realizuje krok związany z: „start intranet fetch”.
  - `  - Metoda `MainWindowHandlers._on_intranet_ready()`` — linie **1874-2215**. Funkcja/metoda realizuje krok związany z: „on intranet ready”.
  - `  - Metoda `MainWindowHandlers._format_intranet_datetime()`` — linie **2217-2225**. Funkcja/metoda realizuje krok związany z: „format intranet datetime”.
  - `  - Metoda `MainWindowHandlers._rebuild_intranet_table()`` — linie **2227-2262**. Funkcja/metoda realizuje krok związany z: „rebuild intranet table”.
  - `  - Metoda `MainWindowHandlers._populate_intranet_filters()`` — linie **2264-2283**. Funkcja/metoda realizuje krok związany z: „populate intranet filters”.
  - `  - Metoda `MainWindowHandlers._apply_intranet_filters()`` — linie **2285-2352**. Funkcja/metoda realizuje krok związany z: „apply intranet filters”.
  - `  - Metoda `MainWindowHandlers._on_intranet_error()`` — linie **2354-2397**. Funkcja/metoda realizuje krok związany z: „on intranet error”.
  - `  - Metoda `MainWindowHandlers._make_color_icon()`` — linie **2399-2415**. Funkcja/metoda realizuje krok związany z: „make color icon”.
  - `  - Metoda `MainWindowHandlers._make_action_icon()`` — linie **2417-2456**. Funkcja/metoda realizuje krok związany z: „make action icon”.
  - `  - Metoda `MainWindowHandlers._is_worker_running()`` — linie **2458-2463**. Funkcja/metoda realizuje krok związany z: „is worker running”.
  - `  - Metoda `MainWindowHandlers._set_task_active()`` — linie **2465-2498**. Funkcja/metoda realizuje krok związany z: „set task active”.
  - `  - Metoda `MainWindowHandlers._reset_results_state()`` — linie **2500-2806**. Funkcja/metoda realizuje krok związany z: „reset results state”.
  - `  - Metoda `MainWindowHandlers._update_thread_state()`` — linie **2808-2813**. Funkcja/metoda realizuje krok związany z: „update thread state”.
  - `  - Metoda `MainWindowHandlers._stop_analysis()`` — linie **2815-2843**. Funkcja/metoda realizuje krok związany z: „stop analysis”.
  - `  - Metoda `MainWindowHandlers._start_analysis()`` — linie **2845-2963**. Funkcja/metoda realizuje krok związany z: „start analysis”.
  - `  - Metoda `MainWindowHandlers._on_analysis_error()`` — linie **2965-2998**. Funkcja/metoda realizuje krok związany z: „on analysis error”.
  - `  - Metoda `MainWindowHandlers._on_analysis_finished()`` — linie **3000-3331**. Funkcja/metoda realizuje krok związany z: „on analysis finished”.
  - `  - Metoda `MainWindowHandlers._populate_analysis_filters()`` — linie **3333-3362**. Funkcja/metoda realizuje krok związany z: „populate analysis filters”.
  - `  - Metoda `MainWindowHandlers._update_analysis_pin_options()`` — linie **3364-3374**. Funkcja/metoda realizuje krok związany z: „update analysis pin options”.
  - `  - Metoda `MainWindowHandlers._update_analysis_step_options()`` — linie **3376-3397**. Funkcja/metoda realizuje krok związany z: „update analysis step options”.
  - `  - Metoda `MainWindowHandlers._update_analysis_param_options()`` — linie **3399-3422**. Funkcja/metoda realizuje krok związany z: „update analysis param options”.
  - `  - Metoda `MainWindowHandlers._on_analysis_machine_changed()`` — linie **3424-3426**. Funkcja/metoda realizuje krok związany z: „on analysis machine changed”.
  - `  - Metoda `MainWindowHandlers._on_analysis_pin_changed()`` — linie **3428-3430**. Funkcja/metoda realizuje krok związany z: „on analysis pin changed”.
  - `  - Metoda `MainWindowHandlers._on_analysis_step_changed()`` — linie **3432-3434**. Funkcja/metoda realizuje krok związany z: „on analysis step changed”.
  - `  - Metoda `MainWindowHandlers._apply_analysis_filters()`` — linie **3436-3495**. Funkcja/metoda realizuje krok związany z: „apply analysis filters”.
  - `  - Metoda `MainWindowHandlers._set_combo_items()`` — linie **3497-3520**. Funkcja/metoda realizuje krok związany z: „set combo items”.
  - `  - Metoda `MainWindowHandlers._populate_param_line_filters()`` — linie **3522-3550**. Funkcja/metoda realizuje krok związany z: „populate param line filters”.
  - `  - Metoda `MainWindowHandlers._update_param_line_pin_options()`` — linie **3552-3564**. Funkcja/metoda realizuje krok związany z: „update param line pin options”.
  - `  - Metoda `MainWindowHandlers._update_param_line_step_options()`` — linie **3566-3588**. Funkcja/metoda realizuje krok związany z: „update param line step options”.
  - `  - Metoda `MainWindowHandlers._on_param_line_machine_changed()`` — linie **3590-3591**. Funkcja/metoda realizuje krok związany z: „on param line machine changed”.
  - `  - Metoda `MainWindowHandlers._on_param_line_pin_changed()`` — linie **3593-3594**. Funkcja/metoda realizuje krok związany z: „on param line pin changed”.
  - `  - Metoda `MainWindowHandlers._apply_param_line_filters()`` — linie **3596-3630**. Funkcja/metoda realizuje krok związany z: „apply param line filters”.
  - `  - Metoda `MainWindowHandlers._clear_param_line_charts()`` — linie **3632-3637**. Funkcja/metoda realizuje krok związany z: „clear param line charts”.
  - `  - Metoda `MainWindowHandlers._refresh_hp_grip_columns()`` — linie **3639-3667**. Funkcja/metoda realizuje krok związany z: „refresh hp grip columns”.
  - `  - Metoda `MainWindowHandlers._refresh_nest_columns()`` — linie **3669-3699**. Funkcja/metoda realizuje krok związany z: „refresh nest columns”.
  - `  - Metoda `MainWindowHandlers._refresh_stripping_columns()`` — linie **3701-3747**. Funkcja/metoda realizuje krok związany z: „refresh stripping columns”.
  - `  - Metoda `MainWindowHandlers._configure_hp_grip_table()`` — linie **3749-3766**. Funkcja/metoda realizuje krok związany z: „configure hp grip table”.
  - `  - Metoda `MainWindowHandlers._configure_nest_table()`` — linie **3768-3785**. Funkcja/metoda realizuje krok związany z: „configure nest table”.
  - `  - Metoda `MainWindowHandlers._configure_stripping_table()`` — linie **3787-3804**. Funkcja/metoda realizuje krok związany z: „configure stripping table”.
  - `  - Metoda `MainWindowHandlers._populate_hp_grip_filters()`` — linie **3806-3823**. Funkcja/metoda realizuje krok związany z: „populate hp grip filters”.
  - `  - Metoda `MainWindowHandlers._update_hp_grip_pin_options()`` — linie **3825-3834**. Funkcja/metoda realizuje krok związany z: „update hp grip pin options”.
  - `  - Metoda `MainWindowHandlers._on_hp_grip_machine_changed()`` — linie **3836-3838**. Funkcja/metoda realizuje krok związany z: „on hp grip machine changed”.
  - `  - Metoda `MainWindowHandlers._apply_hp_grip_filters()`` — linie **3840-3883**. Funkcja/metoda realizuje krok związany z: „apply hp grip filters”.
  - `  - Metoda `MainWindowHandlers._populate_nest_filters()`` — linie **3885-3902**. Funkcja/metoda realizuje krok związany z: „populate nest filters”.
  - `  - Metoda `MainWindowHandlers._update_nest_pin_options()`` — linie **3904-3913**. Funkcja/metoda realizuje krok związany z: „update nest pin options”.
  - `  - Metoda `MainWindowHandlers._on_nest_machine_changed()`` — linie **3915-3917**. Funkcja/metoda realizuje krok związany z: „on nest machine changed”.
  - `  - Metoda `MainWindowHandlers._apply_nest_filters()`` — linie **3919-3962**. Funkcja/metoda realizuje krok związany z: „apply nest filters”.
  - `  - Metoda `MainWindowHandlers._populate_stripping_filters()`` — linie **3964-3981**. Funkcja/metoda realizuje krok związany z: „populate stripping filters”.
  - `  - Metoda `MainWindowHandlers._update_stripping_pin_options()`` — linie **3983-3992**. Funkcja/metoda realizuje krok związany z: „update stripping pin options”.
  - `  - Metoda `MainWindowHandlers._on_stripping_machine_changed()`` — linie **3994-3996**. Funkcja/metoda realizuje krok związany z: „on stripping machine changed”.
  - `  - Metoda `MainWindowHandlers._apply_stripping_filters()`` — linie **3998-4044**. Funkcja/metoda realizuje krok związany z: „apply stripping filters”.
  - `  - Metoda `MainWindowHandlers._pareto_target_label()`` — linie **4046-4053**. Funkcja/metoda realizuje krok związany z: „pareto target label”.
  - `  - Metoda `MainWindowHandlers._pareto_source_label()`` — linie **4055-4062**. Funkcja/metoda realizuje krok związany z: „pareto source label”.
  - `  - Metoda `MainWindowHandlers._populate_pareto_filters()`` — linie **4064-4073**. Funkcja/metoda realizuje krok związany z: „populate pareto filters”.
  - `  - Metoda `MainWindowHandlers._update_pareto_chart()`` — linie **4075-4113**. Funkcja/metoda realizuje krok związany z: „update pareto chart”.
  - `  - Metoda `MainWindowHandlers._populate_param_card_filters()`` — linie **4115-4177**. Funkcja/metoda realizuje krok związany z: „populate param card filters”.
  - `  - Metoda `MainWindowHandlers._on_param_card_datetime_changed()`` — linie **4179-4198**. Funkcja/metoda realizuje krok związany z: „on param card datetime changed”.
  - `  - Metoda `MainWindowHandlers._update_param_card_datetime_options()`` — linie **4200-4229**. Funkcja/metoda realizuje krok związany z: „update param card datetime options”.
  - `  - Metoda `MainWindowHandlers._on_param_card_machine_changed()`` — linie **4231-4249**. Funkcja/metoda realizuje krok związany z: „on param card machine changed”.
  - `  - Metoda `MainWindowHandlers._set_param_card_group()`` — linie **4251-4394**. Funkcja/metoda realizuje krok związany z: „set param card group”.
  - `  - Metoda `MainWindowHandlers._param_card_header_labels()`` — linie **4396-4424**. Funkcja/metoda realizuje krok związany z: „param card header labels”.
  - `  - Metoda `MainWindowHandlers._update_param_card_table()`` — linie **4426-4504**. Funkcja/metoda realizuje krok związany z: „update param card table”.
  - `  - Metoda `MainWindowHandlers._param_card_struct_text()`` — linie **4506-4508**. Funkcja/metoda realizuje krok związany z: „param card struct text”.
  - `  - Metoda `MainWindowHandlers._param_card_find_struct_snapshot()`` — linie **4510-4530**. Funkcja/metoda realizuje krok związany z: „param card find struct snapshot”.
  - `  - Metoda `MainWindowHandlers._param_card_cell_text()`` — linie **4532-4633**. Funkcja/metoda realizuje krok związany z: „param card cell text”.
  - `  - Metoda `MainWindowHandlers._populate_index_line_filters()`` — linie **4635-4663**. Funkcja/metoda realizuje krok związany z: „populate index line filters”.
  - `  - Metoda `MainWindowHandlers._update_index_line_table_options()`` — linie **4665-4677**. Funkcja/metoda realizuje krok związany z: „update index line table options”.
  - `  - Metoda `MainWindowHandlers._update_index_line_step_options()`` — linie **4679-4701**. Funkcja/metoda realizuje krok związany z: „update index line step options”.
  - `  - Metoda `MainWindowHandlers._on_index_line_machine_changed()`` — linie **4703-4704**. Funkcja/metoda realizuje krok związany z: „on index line machine changed”.
  - `  - Metoda `MainWindowHandlers._on_index_line_pin_changed()`` — linie **4706-4707**. Funkcja/metoda realizuje krok związany z: „on index line pin changed”.
  - `  - Metoda `MainWindowHandlers._apply_index_line_filters()`` — linie **4709-4746**. Funkcja/metoda realizuje krok związany z: „apply index line filters”.
  - `  - Metoda `MainWindowHandlers._clear_index_line_charts()`` — linie **4748-4753**. Funkcja/metoda realizuje krok związany z: „clear index line charts”.
  - `  - Metoda `MainWindowHandlers._populate_index_filters()`` — linie **4755-4776**. Funkcja/metoda realizuje krok związany z: „populate index filters”.
  - `  - Metoda `MainWindowHandlers._update_index_table_options()`` — linie **4778-4788**. Funkcja/metoda realizuje krok związany z: „update index table options”.
  - `  - Metoda `MainWindowHandlers._update_index_step_options()`` — linie **4790-4811**. Funkcja/metoda realizuje krok związany z: „update index step options”.
  - `  - Metoda `MainWindowHandlers._update_index_param_options()`` — linie **4813-4843**. Funkcja/metoda realizuje krok związany z: „update index param options”.
  - `  - Metoda `MainWindowHandlers._on_index_machine_changed()`` — linie **4845-4847**. Funkcja/metoda realizuje krok związany z: „on index machine changed”.
  - `  - Metoda `MainWindowHandlers._on_index_table_changed()`` — linie **4849-4851**. Funkcja/metoda realizuje krok związany z: „on index table changed”.
  - `  - Metoda `MainWindowHandlers._on_index_step_changed()`` — linie **4853-4855**. Funkcja/metoda realizuje krok związany z: „on index step changed”.
  - `  - Metoda `MainWindowHandlers._apply_index_filters()`` — linie **4857-4912**. Funkcja/metoda realizuje krok związany z: „apply index filters”.
  - `  - Metoda `MainWindowHandlers._format_index_value()`` — linie **4914-4926**. Funkcja/metoda realizuje krok związany z: „format index value”.
  - `  - Metoda `MainWindowHandlers._format_override_value()`` — linie **4928-4934**. Funkcja/metoda realizuje krok związany z: „format override value”.
  - `  - Metoda `MainWindowHandlers._normalize_struct_scalar()`` — linie **4937-4950**. Funkcja/metoda realizuje krok związany z: „normalize struct scalar”.
  - `  - Metoda `MainWindowHandlers._format_struct_value()`` — linie **4953-4966**. Funkcja/metoda realizuje krok związany z: „format struct value”.
  - `  - Metoda `MainWindowHandlers._build_struct_change_events()`` — linie **4968-5022**. Funkcja/metoda realizuje krok związany z: „build struct change events”.
  - `  - Metoda `MainWindowHandlers._build_index_events()`` — linie **5024-5124**. Funkcja/metoda realizuje krok związany z: „build index events”.
  - `  - Metoda `MainWindowHandlers._normalize_event_text()`` — linie **5127-5145**. Funkcja/metoda realizuje krok związany z: „normalize event text”.
  - `  - Metoda `MainWindowHandlers._event_dt_key()`` — linie **5148-5151**. Funkcja/metoda realizuje krok związany z: „event dt key”.
  - `  - Metoda `MainWindowHandlers._merge_event_paths()`` — linie **5153-5165**. Funkcja/metoda realizuje krok związany z: „merge event paths”.
  - `  - Metoda `MainWindowHandlers._deduplicate_param_events()`` — linie **5167-5194**. Funkcja/metoda realizuje krok związany z: „deduplicate param events”.
  - `  - Metoda `MainWindowHandlers._deduplicate_index_events()`` — linie **5196-5236**. Funkcja/metoda realizuje krok związany z: „deduplicate index events”.
  - `  - Metoda `MainWindowHandlers._collapse_repeated_index_events()`` — linie **5238-5285**. Funkcja/metoda realizuje krok związany z: „collapse repeated index events”.
  - `  - Metoda `MainWindowHandlers._fill_change_trees()`` — linie **5287-5500**. Funkcja/metoda realizuje krok związany z: „fill change trees”.
  - `  - Metoda `MainWindowHandlers._on_top_issue_click()`` — linie **5502-5542**. Funkcja/metoda realizuje krok związany z: „on top issue click”.
  - `  - Metoda `MainWindowHandlers._on_change_tree_click()`` — linie **5544-5574**. Funkcja/metoda realizuje krok związany z: „on change tree click”.
  - `  - Metoda `MainWindowHandlers._set_combo()`` — linie **5576-5584**. Funkcja/metoda realizuje krok związany z: „set combo”.
  - `  - Metoda `MainWindowHandlers._fill_program_changes_table()`` — linie **5586-5595**. Funkcja/metoda realizuje krok związany z: „fill program changes table”.
  - `  - Metoda `MainWindowHandlers._populate_program_filters()`` — linie **5597-5605**. Funkcja/metoda realizuje krok związany z: „populate program filters”.
  - `  - Metoda `MainWindowHandlers._populate_trend_filters()`` — linie **5607-5614**. Funkcja/metoda realizuje krok związany z: „populate trend filters”.
  - `  - Metoda `MainWindowHandlers._apply_trend_filters()`` — linie **5616-5766**. Funkcja/metoda realizuje krok związany z: „apply trend filters”.
  - `  - Metoda `MainWindowHandlers._apply_program_filters()`` — linie **5768-5791**. Funkcja/metoda realizuje krok związany z: „apply program filters”.
  - `  - Metoda `MainWindowHandlers._export_top_issues_csv()`` — linie **5793-5822**. Funkcja/metoda realizuje krok związany z: „export top issues csv”.
  - `  - Metoda `MainWindowHandlers._export_change_tree_csv()`` — linie **5824-5906**. Funkcja/metoda realizuje krok związany z: „export change tree csv”.
  - `  - Metoda `MainWindowHandlers._export_tree_csv()`` — linie **5908-5973**. Funkcja/metoda realizuje krok związany z: „export tree csv”.
  - `  - Metoda `MainWindowHandlers._export_analysis_csv()`` — linie **5975-6000**. Funkcja/metoda realizuje krok związany z: „export analysis csv”.
  - `  - Metoda `MainWindowHandlers._export_index_csv()`` — linie **6002-6030**. Funkcja/metoda realizuje krok związany z: „export index csv”.
  - `  - Metoda `MainWindowHandlers._export_programs_csv()`` — linie **6032-6052**. Funkcja/metoda realizuje krok związany z: „export programs csv”.
  - `  - Metoda `MainWindowHandlers._export_param_card_csv()`` — linie **6054-6135**. Funkcja/metoda realizuje krok związany z: „export param card csv”.
  - `  - Metoda `MainWindowHandlers._export_intranet_csv()`` — linie **6137-6177**. Funkcja/metoda realizuje krok związany z: „export intranet csv”.

## Plik: `hfm_analyzer/gui/main_window.py`
- **Rola pliku:** Moduł pomocniczy spinający importy i punkty wejścia.
- **Elementy kodu (z zakresem linii):**
  - `Funkcja `_label()`` — linie **67-72**. Funkcja/metoda realizuje krok związany z: „label”.
  - `Klasa `ModernMainWindow`` — linie **75-727**. Klasa odpowiedzialna za obszar: „ModernMainWindow”.
  - `  - Metoda `ModernMainWindow.__init__()`` — linie **76-653**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `ModernMainWindow._post_init_load()`` — linie **655-703**. Funkcja/metoda realizuje krok związany z: „post init load”.
  - `  - Metoda `ModernMainWindow._open_line_chart_zoom()`` — linie **705-727**. Funkcja/metoda realizuje krok związany z: „open line chart zoom”.

## Plik: `hfm_analyzer/gui/tabs/__init__.py`
- **Rola pliku:** Budowa pojedynczej zakładki interfejsu użytkownika.
- **Elementy kodu:** brak jawnych funkcji/klas; plik zawiera głównie stałe, importy lub inicjalizację pakietu.

## Plik: `hfm_analyzer/gui/tabs/changes_chart_tab.py`
- **Rola pliku:** Budowa pojedynczej zakładki interfejsu użytkownika.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `ChangesChartTab`` — linie **15-50**. Klasa odpowiedzialna za obszar: „ChangesChartTab”.
  - `  - Metoda `ChangesChartTab.__init__()`` — linie **18-21**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `ChangesChartTab._build_ui()`` — linie **23-50**. Funkcja/metoda realizuje krok związany z: „build ui”.

## Plik: `hfm_analyzer/gui/tabs/changes_tab.py`
- **Rola pliku:** Budowa pojedynczej zakładki interfejsu użytkownika.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `ChangesTab`` — linie **34-310**. Klasa odpowiedzialna za obszar: „ChangesTab”.
  - `  - Metoda `ChangesTab.__init__()`` — linie **37-45**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `ChangesTab._build_ui()`` — linie **47-310**. Funkcja/metoda realizuje krok związany z: „build ui”.

## Plik: `hfm_analyzer/gui/tabs/gripper_tab.py`
- **Rola pliku:** Budowa pojedynczej zakładki interfejsu użytkownika.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `GripperTab`` — linie **21-55**. Klasa odpowiedzialna za obszar: „GripperTab”.
  - `  - Metoda `GripperTab.__init__()`` — linie **24-27**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `GripperTab._build_ui()`` — linie **29-55**. Funkcja/metoda realizuje krok związany z: „build ui”.

## Plik: `hfm_analyzer/gui/tabs/nest_tab.py`
- **Rola pliku:** Budowa pojedynczej zakładki interfejsu użytkownika.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `NestTab`` — linie **21-55**. Klasa odpowiedzialna za obszar: „NestTab”.
  - `  - Metoda `NestTab.__init__()`` — linie **24-27**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `NestTab._build_ui()`` — linie **29-55**. Funkcja/metoda realizuje krok związany z: „build ui”.

## Plik: `hfm_analyzer/gui/tabs/parameter_changes_tab.py`
- **Rola pliku:** Budowa pojedynczej zakładki interfejsu użytkownika.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `ParameterChangesTab`` — linie **25-125**. Klasa odpowiedzialna za obszar: „ParameterChangesTab”.
  - `  - Metoda `ParameterChangesTab.__init__()`` — linie **28-31**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `ParameterChangesTab._build_ui()`` — linie **33-125**. Funkcja/metoda realizuje krok związany z: „build ui”.

## Plik: `hfm_analyzer/gui/tabs/program_changes_tab.py`
- **Rola pliku:** Budowa pojedynczej zakładki interfejsu użytkownika.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `ProgramChangesTab`` — linie **23-79**. Klasa odpowiedzialna za obszar: „ProgramChangesTab”.
  - `  - Metoda `ProgramChangesTab.__init__()`` — linie **26-29**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `ProgramChangesTab._build_ui()`` — linie **31-79**. Funkcja/metoda realizuje krok związany z: „build ui”.

## Plik: `hfm_analyzer/gui/tabs/stripping_tab.py`
- **Rola pliku:** Budowa pojedynczej zakładki interfejsu użytkownika.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `StrippingTab`` — linie **21-55**. Klasa odpowiedzialna za obszar: „StrippingTab”.
  - `  - Metoda `StrippingTab.__init__()`` — linie **24-27**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `StrippingTab._build_ui()`` — linie **29-55**. Funkcja/metoda realizuje krok związany z: „build ui”.

## Plik: `hfm_analyzer/gui/utils.py`
- **Rola pliku:** Narzędzia GUI: sortowanie naturalne i pomoc przy mapowaniu dysków sieciowych.
- **Elementy kodu (z zakresem linii):**
  - `Funkcja `_available_drive_letters()`` — linie **38-64**. Funkcja/metoda realizuje krok związany z: „available drive letters”.
  - `Funkcja `_maybe_offer_drive_mapping()`` — linie **67-137**. Funkcja/metoda realizuje krok związany z: „maybe offer drive mapping”.
  - `Funkcja `_natural_sort_key()`` — linie **140-157**. Funkcja/metoda realizuje krok związany z: „natural sort key”.

## Plik: `hfm_analyzer/gui/widgets.py`
- **Rola pliku:** Własne widżety wykresów (pie/bar/pareto/line) i delegaty rysowania.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `PieChartWidget`` — linie **18-145**. Klasa odpowiedzialna za obszar: „PieChartWidget”.
  - `  - Metoda `PieChartWidget.__init__()`` — linie **21-31**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `PieChartWidget.set_data()`` — linie **33-40**. Funkcja/metoda realizuje krok związany z: „set data”.
  - `  - Metoda `PieChartWidget.set_colors()`` — linie **42-49**. Funkcja/metoda realizuje krok związany z: „set colors”.
  - `  - Metoda `PieChartWidget.paintEvent()`` — linie **51-97**. Funkcja/metoda realizuje krok związany z: „paintEvent”.
  - `  - Metoda `PieChartWidget.mouseMoveEvent()`` — linie **99-138**. Funkcja/metoda realizuje krok związany z: „mouseMoveEvent”.
  - `  - Metoda `PieChartWidget.leaveEvent()`` — linie **140-145**. Funkcja/metoda realizuje krok związany z: „leaveEvent”.
  - `Klasa `BarChartWidget`` — linie **147-450**. Klasa odpowiedzialna za obszar: „BarChartWidget”.
  - `  - Metoda `BarChartWidget.__init__()`` — linie **150-165**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `BarChartWidget.set_data()`` — linie **167-176**. Funkcja/metoda realizuje krok związany z: „set data”.
  - `  - Metoda `BarChartWidget.set_colors()`` — linie **178-186**. Funkcja/metoda realizuje krok związany z: „set colors”.
  - `  - Metoda `BarChartWidget.set_overlay()`` — linie **188-195**. Funkcja/metoda realizuje krok związany z: „set overlay”.
  - `  - Metoda `BarChartWidget.set_overlay_min_ymax()`` — linie **197-206**. Funkcja/metoda realizuje krok związany z: „set overlay min ymax”.
  - `  - Metoda `BarChartWidget.paintEvent()`` — linie **208-390**. Funkcja/metoda realizuje krok związany z: „paintEvent”.
  - `  - Metoda `BarChartWidget.mouseMoveEvent()`` — linie **392-442**. Funkcja/metoda realizuje krok związany z: „mouseMoveEvent”.
  - `  - Metoda `BarChartWidget.leaveEvent()`` — linie **444-450**. Funkcja/metoda realizuje krok związany z: „leaveEvent”.
  - `Klasa `ParetoChartWidget`` — linie **452-768**. Klasa odpowiedzialna za obszar: „ParetoChartWidget”.
  - `  - Metoda `ParetoChartWidget.__init__()`` — linie **455-471**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `ParetoChartWidget.set_data()`` — linie **473-563**. Funkcja/metoda realizuje krok związany z: „set data”.
  - `  - Metoda `ParetoChartWidget.paintEvent()`` — linie **565-705**. Funkcja/metoda realizuje krok związany z: „paintEvent”.
  - `  - Metoda `ParetoChartWidget.mouseMoveEvent()`` — linie **707-760**. Funkcja/metoda realizuje krok związany z: „mouseMoveEvent”.
  - `  - Metoda `ParetoChartWidget.leaveEvent()`` — linie **762-768**. Funkcja/metoda realizuje krok związany z: „leaveEvent”.
  - `Klasa `LineChartWidget`` — linie **770-983**. Klasa odpowiedzialna za obszar: „LineChartWidget”.
  - `  - Metoda `LineChartWidget.__init__()`` — linie **773-783**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `LineChartWidget.set_series()`` — linie **785-811**. Funkcja/metoda realizuje krok związany z: „set series”.
  - `  - Metoda `LineChartWidget.series_snapshot()`` — linie **813-814**. Funkcja/metoda realizuje krok związany z: „series snapshot”.
  - `  - Metoda `LineChartWidget.paintEvent()`` — linie **816-939**. Funkcja/metoda realizuje krok związany z: „paintEvent”.
  - `  - Metoda `LineChartWidget.mouseMoveEvent()`` — linie **941-976**. Funkcja/metoda realizuje krok związany z: „mouseMoveEvent”.
  - `  - Metoda `LineChartWidget.leaveEvent()`` — linie **978-983**. Funkcja/metoda realizuje krok związany z: „leaveEvent”.
  - `Klasa `CountBadgeDelegate`` — linie **985-1023**. Klasa odpowiedzialna za obszar: „CountBadgeDelegate”.
  - `  - Metoda `CountBadgeDelegate.paint()`` — linie **988-1020**. Funkcja/metoda realizuje krok związany z: „paint”.
  - `  - Metoda `CountBadgeDelegate.sizeHint()`` — linie **1022-1023**. Funkcja/metoda realizuje krok związany z: „sizeHint”.

## Plik: `hfm_analyzer/models.py`
- **Rola pliku:** Modele danych (dataclass) reprezentujące odczytane snapshoty.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `FoundFile`` — linie **11-16**. Klasa odpowiedzialna za obszar: „FoundFile”.
  - `Klasa `ParamSnapshot`` — linie **20-32**. Klasa odpowiedzialna za obszar: „ParamSnapshot”.
  - `Klasa `IndexSnapshot`` — linie **36-48**. Klasa odpowiedzialna za obszar: „IndexSnapshot”.
  - `Klasa `GripSnapshot`` — linie **52-60**. Klasa odpowiedzialna za obszar: „GripSnapshot”.
  - `Klasa `NestSnapshot`` — linie **64-72**. Klasa odpowiedzialna za obszar: „NestSnapshot”.
  - `Klasa `HairpinSnapshot`` — linie **76-84**. Klasa odpowiedzialna za obszar: „HairpinSnapshot”.

## Plik: `hfm_analyzer/storage/__init__.py`
- **Rola pliku:** Plik inicjalizacyjny pakietu.
- **Elementy kodu:** brak jawnych funkcji/klas; plik zawiera głównie stałe, importy lub inicjalizację pakietu.

## Plik: `hfm_analyzer/storage/runtime_sqlite_cache.py`
- **Rola pliku:** Warstwa trwałej/pół-trwałej pamięci podręcznej SQLite dla danych analitycznych.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `RuntimeSQLiteCache`` — linie **24-1282**. Klasa odpowiedzialna za obszar: „RuntimeSQLiteCache”.
  - `  - Metoda `RuntimeSQLiteCache.__init__()`` — linie **27-41**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `RuntimeSQLiteCache._connect()`` — linie **43-53**. Funkcja/metoda realizuje krok związany z: „connect”.
  - `  - Metoda `RuntimeSQLiteCache._get_connection()`` — linie **55-60**. Funkcja/metoda realizuje krok związany z: „get connection”.
  - `  - Metoda `RuntimeSQLiteCache._init_schema()`` — linie **62-220**. Funkcja/metoda realizuje krok związany z: „init schema”.
  - `  - Metoda `RuntimeSQLiteCache.close()`` — linie **222-237**. Funkcja/metoda realizuje krok związany z: „close”.
  - `  - Metoda `RuntimeSQLiteCache.reset()`` — linie **239-261**. Funkcja/metoda realizuje krok związany z: „reset”.
  - `  - Metoda `RuntimeSQLiteCache.purge_older_than()`` — linie **264-329**. Funkcja/metoda realizuje krok związany z: „purge older than”.
  - `  - Metoda `RuntimeSQLiteCache._ensure_machine()`` — linie **331-352**. Funkcja/metoda realizuje krok związany z: „ensure machine”.
  - `  - Metoda `RuntimeSQLiteCache._hour_bucket_ts()`` — linie **355-357**. Funkcja/metoda realizuje krok związany z: „hour bucket ts”.
  - `  - Metoda `RuntimeSQLiteCache.has_hour_bucket()`` — linie **359-397**. Funkcja/metoda realizuje krok związany z: „has hour bucket”.
  - `  - Metoda `RuntimeSQLiteCache.record_hour_bucket()`` — linie **399-407**. Funkcja/metoda realizuje krok związany z: „record hour bucket”.
  - `  - Metoda `RuntimeSQLiteCache.has_file()`` — linie **409-416**. Funkcja/metoda realizuje krok związany z: „has file”.
  - `  - Metoda `RuntimeSQLiteCache.record_file()`` — linie **418-440**. Funkcja/metoda realizuje krok związany z: „record file”.
  - `  - Metoda `RuntimeSQLiteCache._transaction()`` — linie **443-453**. Funkcja/metoda realizuje krok związany z: „transaction”.
  - `  - Metoda `RuntimeSQLiteCache.insert_param_snapshots()`` — linie **455-495**. Funkcja/metoda realizuje krok związany z: „insert param snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.insert_index_snapshots()`` — linie **497-537**. Funkcja/metoda realizuje krok związany z: „insert index snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.insert_grip_snapshots()`` — linie **539-545**. Funkcja/metoda realizuje krok związany z: „insert grip snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.insert_nest_snapshots()`` — linie **547-553**. Funkcja/metoda realizuje krok związany z: „insert nest snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.insert_hairpin_snapshots()`` — linie **555-561**. Funkcja/metoda realizuje krok związany z: „insert hairpin snapshots”.
  - `  - Metoda `RuntimeSQLiteCache._insert_struct_snapshots()`` — linie **563-598**. Funkcja/metoda realizuje krok związany z: „insert struct snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.iter_param_snapshots()`` — linie **600-691**. Funkcja/metoda realizuje krok związany z: „iter param snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_param_snapshots()`` — linie **693-714**. Funkcja/metoda realizuje krok związany z: „fetch param snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.iter_index_snapshots()`` — linie **716-805**. Funkcja/metoda realizuje krok związany z: „iter index snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_index_snapshots_list()`` — linie **807-828**. Funkcja/metoda realizuje krok związany z: „fetch index snapshots list”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_struct_snapshots()`` — linie **830-906**. Funkcja/metoda realizuje krok związany z: „fetch struct snapshots”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_struct_value_keys()`` — linie **908-913**. Funkcja/metoda realizuje krok związany z: „fetch struct value keys”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_machine_names()`` — linie **915-918**. Funkcja/metoda realizuje krok związany z: „fetch machine names”.
  - `  - Metoda `RuntimeSQLiteCache._parse_file_dt()`` — linie **921-935**. Funkcja/metoda realizuje krok związany z: „parse file dt”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_files()`` — linie **937-971**. Funkcja/metoda realizuje krok związany z: „fetch files”.
  - `  - Metoda `RuntimeSQLiteCache.insert_intranet_rows()`` — linie **973-1021**. Funkcja/metoda realizuje krok związany z: „insert intranet rows”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_intranet_rows()`` — linie **1023-1070**. Funkcja/metoda realizuje krok związany z: „fetch intranet rows”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_time_bounds()`` — linie **1072-1116**. Funkcja/metoda realizuje krok związany z: „fetch time bounds”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_param_line_hierarchy()`` — linie **1118-1164**. Funkcja/metoda realizuje krok związany z: „fetch param line hierarchy”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_index_line_hierarchy()`` — linie **1166-1212**. Funkcja/metoda realizuje krok związany z: „fetch index line hierarchy”.
  - `  - Metoda `RuntimeSQLiteCache.fetch_param_card_groups()`` — linie **1214-1267**. Funkcja/metoda realizuje krok związany z: „fetch param card groups”.
  - `  - Metoda `RuntimeSQLiteCache.stats()`` — linie **1269-1282**. Funkcja/metoda realizuje krok związany z: „stats”.

## Plik: `hfm_analyzer/utils.py`
- **Rola pliku:** Niskopoziomowe narzędzia systemowe i sieciowe (UNC, mapowanie dysków, dostępność).
- **Elementy kodu (z zakresem linii):**
  - `Funkcja `_split_unc()`` — linie **11-16**. Funkcja/metoda realizuje krok związany z: „split unc”.
  - `Funkcja `_core_unc()`` — linie **19-23**. Funkcja/metoda realizuje krok związany z: „core unc”.
  - `Funkcja `_core_and_rest()`` — linie **26-34**. Funkcja/metoda realizuje krok związany z: „core and rest”.
  - `Funkcja `extract_unc_share()`` — linie **37-43**. Funkcja/metoda realizuje krok związany z: „extract unc share”.
  - `Funkcja `list_mapped_network_drives()`` — linie **46-103**. Funkcja/metoda realizuje krok związany z: „list mapped network drives”.
  - `Funkcja `map_unc_to_drive_if_possible()`` — linie **106-139**. Funkcja/metoda realizuje krok związany z: „map unc to drive if possible”.
  - `Funkcja `map_network_drive()`` — linie **142-159**. Funkcja/metoda realizuje krok związany z: „map network drive”.
  - `Funkcja `network_path_available()`` — linie **162-170**. Funkcja/metoda realizuje krok związany z: „network path available”.
  - `Funkcja `sqlite_cache_available()`` — linie **173-188**. Funkcja/metoda realizuje krok związany z: „sqlite cache available”.

## Plik: `hfm_analyzer/workers.py`
- **Rola pliku:** Wątki robocze do skanowania plików, analiz i pobierania danych intranetowych.
- **Elementy kodu (z zakresem linii):**
  - `Klasa `ScanWorker`` — linie **39-105**. Klasa odpowiedzialna za obszar: „ScanWorker”.
  - `  - Metoda `ScanWorker.__init__()`` — linie **46-51**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `ScanWorker.run()`` — linie **53-105**. Funkcja/metoda realizuje krok związany z: „run”.
  - `Klasa `AnalyzeWorker`` — linie **111-744**. Klasa odpowiedzialna za obszar: „AnalyzeWorker”.
  - `  - Metoda `AnalyzeWorker.__init__()`` — linie **118-145**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `AnalyzeWorker.run()`` — linie **147-246**. Funkcja/metoda realizuje krok związany z: „run”.
  - `  - Metoda `AnalyzeWorker._analyze_file()`` — linie **249-744**. Funkcja/metoda realizuje krok związany z: „analyze file”.
  - `Klasa `IntranetWorker`` — linie **747-939**. Klasa odpowiedzialna za obszar: „IntranetWorker”.
  - `  - Metoda `IntranetWorker.__init__()`` — linie **754-775**. Funkcja/metoda realizuje krok związany z: „init”.
  - `  - Metoda `IntranetWorker.run()`` — linie **777-783**. Funkcja/metoda realizuje krok związany z: „run”.
  - `  - Metoda `IntranetWorker._fetch()`` — linie **785-939**. Funkcja/metoda realizuje krok związany z: „fetch”.

## Plik: `main.py`
- **Rola pliku:** Minimalny punkt startowy aplikacji desktopowej.
- **Elementy kodu:** brak jawnych funkcji/klas; plik zawiera głównie stałe, importy lub inicjalizację pakietu.
