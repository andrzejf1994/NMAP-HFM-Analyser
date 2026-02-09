# HFM Analyzer – dokumentacja użytkownika (PL)

## Cel aplikacji (opis prostym językiem)
HFM Analyzer to narzędzie do **przeglądu i porównywania zmian w plikach backupów maszyn**. Program przeszukuje katalogi z kopią parametrów maszyn (XML), porównuje kolejne zapisy, a następnie pokazuje **co się zmieniało, kiedy, na jakiej maszynie oraz w jakich parametrach**. Dodatkowo agreguje i wizualizuje wyniki na wykresach, umożliwia eksport do CSV oraz potrafi pobrać dane NOK z intranetu.

Poniżej znajduje się kompletna instrukcja użytkownika „od uruchomienia do kliknięcia każdego przycisku”.

---

## 1. Uruchomienie aplikacji

### 1.1. Start programu
Program uruchamiasz poleceniem:
```bash
python main.py
```
W tle wykonuje się:
1. Inicjalizacja Qt i ustawienie wyglądu (styl „Fusion”, jasna paleta).
2. Ustawienie ikon aplikacji (jeśli `icon.ico` jest dostępne).
3. Sprawdzenie ustawionego katalogu z backupami (sieciowy lub lokalny).
4. Otworzenie głównego okna.

Źródło: `hfm_analyzer/app.py`.

---

## 2. Procesy zachodzące w tle

Program wykorzystuje **wątki (QThread)**, aby nie blokować interfejsu.

### 2.1. `ScanWorker` – skanowanie backupów
**Co robi:** skanuje strukturę katalogów w podanym zakresie dat (po dniach) i wyszukuje pliki XML pasujące do wzorca.  
**Efekt:** lista znalezionych plików (`FoundFile`) przekazywana do analizy.

Źródło: `hfm_analyzer/workers.py`.

### 2.2. `AnalyzeWorker` – analiza parametrów
**Co robi:** równolegle (ThreadPool) parsuje pliki XML i wyciąga:
- parametry kinematyki (ParamSnapshot),
- parametry stołu/indexu (IndexSnapshot),
- dane grippera (GripSnapshot),
- dane nest (NestSnapshot),
- dane hairpin (HairpinSnapshot).

**Uwaga:** jeśli dostępny jest `lxml`, parser jest szybszy; w przeciwnym razie używany jest standardowy `xml.etree`.

Źródło: `hfm_analyzer/workers.py`.

### 2.3. `IntranetWorker` – pobieranie NOK z intranetu
**Co robi:** wysyła zapytanie HTTP POST do serwisu intranetowego i analizuje tabelę wyników (NOK).  
**Efekt:** lista wpisów NOK oraz ich agregacja w czasie (serie czasowe).

Źródło: `hfm_analyzer/workers.py`.

---

## 3. Główne okno – elementy wspólne

### 3.1. Pasek narzędzi (góra)
- **Tytuł „HFM Analyzer”** – tylko informacyjny.
- **„Linia: …”** – aktualna ścieżka lub nazwa linii (z ustawień).
- **Przycisk „Ustawienia”** – otwiera okno konfiguracji.

Źródło: `hfm_analyzer/gui/main_window.py`.

### 3.2. Filtry i zakres (panel po lewej stronie)
Wspólny panel dla zakładki „Zmiany” (lewa część ekranu).

**Sekcja „Maszyny”:**
- Lista maszyn (wielokrotny wybór).
- Przyciski ikonowe:
  - **Zaznacz wszystkie** – wybiera wszystkie maszyny.
  - **Odznacz wszystkie** – czyści wybór.
  - **Odśwież listę** – ponownie wczytuje katalogi z backupami.

**Zakres dat:**
- **Od:** – data/godzina początkowa.
- **Do:** – data/godzina końcowa.
- **„Rozpocznij analizę”** – startuje skanowanie i analizę.

Źródło: `hfm_analyzer/gui/main_window.py`.

### 3.3. Pasek statusu (dół)
Po uruchomieniu skanowania/analityki pojawiają się:
- **Pasek postępu** – status przetwarzania.
- **Status** – np. „Trwa skanowanie...”, „Zakończono”.
- **Wątki** – informacja o stanie wątków (jeśli widoczna).

Źródło: `hfm_analyzer/gui/main_window.py`.

---

## 4. Okno „Ustawienia”
Otwierane z przycisku **„Ustawienia”**.

### 4.1. Pola i znaczenie
- **Katalog bazowy** – ścieżka do folderu z backupami (sieć lub lokalnie).
- **Wątki analizy (0=auto)** – ile wątków ma użyć analiza (0 = automatycznie).
- **Próg dużej zmiany (%)** – próg do klasyfikacji „dużej zmiany”.
- **ID linii (intranet)** – identyfikator linii używany przy pobieraniu danych.
- **Dni wstecz (Intranet)** – zakres dni do pobrania danych NOK.
- **Wyklucz maszyny (SAP)** – lista maszyn pomijanych w intranecie.

### 4.2. Przyciski
- **Przeglądaj** – wybór katalogu.
- **Ustaw EVO** – szybkie ustawienie domyślnej ścieżki EVO.
- **Ustaw H66 2** – szybkie ustawienie domyślnej ścieżki H66 2.
- **OK** – zapisuje ustawienia.
- **Anuluj** – zamyka bez zapisu.

Źródło: `hfm_analyzer/gui/dialogs.py`.

---

## 5. Zakładki – szczegółowy opis

### 5.1. Zakładka „Zmiany”
Główne podsumowanie skanowania.

**Sekcja „Podsumowanie”:**
- **Liczba zmian** – łączna liczba wykrytych zmian.
- **Liczba maszyn** – liczba maszyn, w których znaleziono zmiany.
- Wykresy:
  - **Wykres kołowy** – udział zmian na maszynach.
  - **Wykres słupkowy / trend** – zmiany w czasie.

**Sekcja „Najbardziej problematyczne miejsca”:**
- Tabela z kolumnami: **Maszyna, Pin, Step, Parametr, Zmian**.
- Kliknięcie wiersza filtruje/odnosi do szczegółów.

**Sekcja „Analiza ilości zmian - Podsumowanie”:**
- Drzewo zmian (Maszyna → Pin → Step → Parametr).
- Przyciski:
  - **Rozwiń wszystko**
  - **Zwiń wszystko**

**Sekcja „Drzewo danych”:**
- Drzewo szczegółów zmian z licznikiem OK/NOK.
- Przyciski:
  - **Rozwiń wszystko**
  - **Zwiń wszystko**

Źródło: `hfm_analyzer/gui/tabs/changes_tab.py`.

---

### 5.2. Zakładka „Wykres zmian”
Pokazuje trend zmian w formie wykresu słupkowego.

**Filtry:**
- **Maszyna** – wybór jednej maszyny lub „wszystkie”.

**Wykres:**
- Zbiorcza liczba zmian w czasie.

Źródło: `hfm_analyzer/gui/tabs/changes_chart_tab.py`.

---

### 5.3. Zakładka „Zmiany Parametrów”
Pokazuje szczegóły zmian parametrów kroków (kinematyka).

**Filtry:**
- **Maszyna**
- **Pin**
- **Step**
- **Parametr**

**Przyciski:**
- **Analizuj zmiany** – uruchamia analizę (AnalyzeWorker).
- **Zatrzymaj analizę** – próba zatrzymania analizy.
- **Eksport CSV** – zapis widocznych wyników do CSV.

**Tabela wyników:**
Kolumny: Data, Czas, Maszyna, Program, Tabela, Pin, Step + lista parametrów (Angle, Nose Locking, Nose Translation, Rotation, Step Speed, Wire Feeding, X, Y) + Ścieżka (ukryta).

Źródło: `hfm_analyzer/gui/tabs/parameter_changes_tab.py`.

---

### 5.4. Zakładka „Zmiany parametrów stołu”
Pokazuje zmiany parametrów „index/stołu”.

**Filtry:**
- **Maszyna**
- **Tabela**
- **Step**
- **Parametr**

**Przycisk:**
- **Eksport CSV** – zapis wyników do CSV.

**Tabela:**
Zawiera parametry index (np. „Index”, „Pionowe kompaktora”, „Zabezpieczenie wewnętrzne”, itp.) oraz Ścieżkę (ukrytą).

Źródło: `hfm_analyzer/gui/main_window.py`.

---

### 5.5. Zakładka „Wykresy parametrów”
Generuje wykresy linii dla parametrów kinematyki.

**Filtry:**
- **Maszyna**
- **Pin**
- **Step**

**Przycisk:**
- **Generuj wykresy** – tworzy wykresy liniowe dla parametrów.

**Wynik:**
Seria wykresów (po jednym na parametr).

Źródło: `hfm_analyzer/gui/main_window.py`.

---

### 5.6. Zakładka „Wykresy parametrów stołu”
Podobna do powyższej, ale dla parametrów stołu/indexu.

**Filtry:**
- **Maszyna**
- **Tablica**
- **Step**

**Przycisk:**
- **Generuj wykresy** – tworzy wykresy dla parametrów stołu.

Źródło: `hfm_analyzer/gui/main_window.py`.

---

### 5.7. Zakładka „Zmiany Programów”
Historia zmian programów na maszynach.

**Filtry:**
- **Maszyna**
- **Stary program**
- **Nowy program**

**Przycisk:**
- **Eksport CSV** – zapis do CSV.

**Tabela:**
Data, Czas, Maszyna, Program (stary → nowy).

Źródło: `hfm_analyzer/gui/tabs/program_changes_tab.py`.

---

### 5.8. Zakładka „Karta parametrów”
Szczegółowy podgląd parametrów dla jednej maszyny i konkretnej daty.

**Filtry:**
- **Maszyna** – aktywna po analizie.
- **Data i godzina** – wybór konkretnej migawki.

**Informacja:**
Krótki opis / status danych („Brak danych” gdy pusto).

**Tabela:**
Program, Tabela, Pin, Step + wszystkie parametry (kinematyka, index, gripper, nest, hairpin).

**Przycisk:**
- **Eksport CSV** – zapis danych do CSV.

Źródło: `hfm_analyzer/gui/main_window.py`.

---

### 5.9. Zakładka „Gripper”
Wyświetla parametry grippera.

**Filtry:**
- **Maszyna**
- **Pin**

**Tabela:**
Dynamicznie generowana z parametrów grippera.

Źródło: `hfm_analyzer/gui/tabs/gripper_tab.py`.

---

### 5.10. Zakładka „Nest”
Wyświetla parametry nest.

**Filtry:**
- **Maszyna**
- **Pin**

**Tabela:**
Dynamicznie generowana z parametrów nest.

Źródło: `hfm_analyzer/gui/tabs/nest_tab.py`.

---

### 5.11. Zakładka „Odizolowanie”
Dane związane z odizolowaniem.

**Filtry:**
- **Maszyna**
- **Pin**

**Tabela:**
Dynamicznie generowana z parametrów odizolowania.

Źródło: `hfm_analyzer/gui/tabs/stripping_tab.py`.

---

### 5.12. Zakładka „Intranet”
Pobiera dane NOK z intranetu i pokazuje w tabeli.

**Filtry (górny rząd):**
- **Maszyna SAP**
- **Maszyna**
- **Źródło (opis)**
- **Źródło (mapa)**

**Filtry (dolny rząd):**
- **Data** – tekstowy filtr daty.
- **Serial No** – tekstowy filtr numeru seryjnego.
- **Ocena** – np. NOK / OK.

**Przycisk:**
- **Eksport CSV** – zapis tabeli do CSV.

Źródło: `hfm_analyzer/gui/main_window.py`.

---

### 5.13. Zakładka „Pareto NOK”
Wykres Pareto dla NOK.

**Filtry:**
- **Maszyna NOK** – wybór maszyny.
- **Filtr nazwy** – tekstowy filtr nazwy maszyny.

**Wynik:**
Wykres Pareto oraz opis podsumowujący.

Źródło: `hfm_analyzer/gui/main_window.py`.

---

### 5.14. Zakładka „Logi”
Konsola tekstowa z komunikatami aplikacji.

**Co się pojawia:**
- Informacje o skanowaniu,
- Analiza plików,
- Błędy i ostrzeżenia,
- Logi z pobierania intranetu.

Źródło: `hfm_analyzer/gui/main_window.py` oraz `hfm_analyzer/gui/handlers.py`.

---

## 6. Co dzieje się po kliknięciu „Rozpocznij analizę”
1. Program sprawdza, czy katalog bazowy istnieje i jest dostępny.
2. Sprawdza, czy zaznaczono przynajmniej jedną maszynę.
3. Sprawdza poprawność zakresu dat.
4. Uruchamia skanowanie (`ScanWorker`).
5. Po skanowaniu automatycznie uruchamia analizę (`AnalyzeWorker`).
6. Aktualizuje dane w zakładkach i w logach.

Źródło: `hfm_analyzer/gui/handlers.py`.

---

## 7. Eksport CSV – gdzie i jak działa
Większość zakładek posiada przycisk **„Eksport CSV”**.  
Po kliknięciu program zapisuje **aktualnie widoczne wyniki** do pliku CSV (zwykle poprzez okno zapisu).

Źródło: `hfm_analyzer/gui/handlers.py`.

---

## 8. Najczęstsze problemy

### 8.1. Brak dostępu do katalogu
Pojawia się okno „Brak dostępu do katalogu sieciowego”.

**Możliwe działania:**
- spróbować ponownie,
- wskazać nowy katalog,
- użyć jednego z presetów (EVO, H66 2),
- zamknąć program.

Źródło: `hfm_analyzer/gui/dialogs.py`.

### 8.2. Brak danych w tabelach
Najczęściej oznacza:
- brak plików w zakresie dat,
- brak uprawnień do katalogu,
- brak analizy (nie uruchomiono „Analizuj zmiany”).

Źródło: `hfm_analyzer/gui/handlers.py`.

