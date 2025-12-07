### ⚠️ Work in Progress

#### You can find the English version of this README below.

---
## Repozytorium

Gałąź `main` zawiera **najnowszą działającą wersję aplikacji**, gotową do instalacji za pomocą skryptu instalacyjnego.  
Gałąź `development` zawiera **wersję roboczą**, nad którą trwają bieżące prace.

➡️ **Instrukcja instalacji znajduje się w sekcji [Instalacja](#Instalacja).**

---

# O aplikacji

PISAK 2.0 to aplikacja do alternatywnej komunikacji, opierająca się o system skanowania z wyborem dokonywanym za pomocą przełącznika. 
Aplikacja powstała w oparciu o projekt [**PISAK**](https://github.com/BrainTech/pisak).
Na ten moment aplikacja składa się z modułu o nazwie **Speller**, który umożliwia komunikację
za pomocą wirtualnej klawiatury wraz z zaimplementowanym mechanizmem predykcji słów.

## Funkcje

### Podstawowa funkcjonalność modułu *Speller*
- **Interfejs skanujący (switch-scanning)**: Nawigacja po elementach interfejsu za pomocą urządzenia przełącznikowego
- **Wirtualna klawiatura**
- **Predykcja słów**: predykcje kolejnych słów generowane z wykorzystaniem modelu LSTM
- **Text-to-Speech**: Odczytywanie wpisanego tekstu przy użyciu silnika Yapper TTS
- **Zarządzanie tekstem**: Zapisywanie i wczytywanie tekstu z plików

## Wymagania

### Wymagania systemowe
- **System operacyjny**: Linux (testowane na dystrybucjach Linux)
- **Python**: min. python 3.10; max. python 3.13
- **Wymagane pakiety**: pełna lista w `requirements.txt`

## Instalacja

Aby zainstalować aplikację, należy pobrać plik [`instaluj.sh`](https://github.com/Julia-M-B/pisak2.0/blob/main/instaluj.sh), a następnie
uruchomić go, korzystając z komendy:

```bash
chmod +x instaluj.sh
./instaluj.sh
```

Skrypt wykona następujące czynności:
1. Sklonuje lub zaktualizuje repozytorium
2. Utworzy wirtualne środowisko Python
3. Zainstaluje wszystkie wymagane zależności
4. Utworzy ikonę na pulpicie dla łatwego dostępu

---
# English version
## Repository

The `main` branch contains **the latest working version of the application**, ready to be installed using the installation script.
The `development` branch contains **the work-in-progress version**, where ongoing development takes place.

➡️ **The installation instructions can be found in the [Installation](#Installation).**

---

# About project

PISAK 2.0 is an alternative communication application based on a scanning system with selection performed using a switch.  
The application was created based on the [**PISAK**](https://github.com/BrainTech/pisak) project.  
At the moment, the application consists of a module called **Speller**, which enables communication through a virtual keyboard with an implemented word prediction mechanism.

## Features

### Core Functionality
- **Switch-Scanning Interface**: navigate through UI elements using a single switch
- **Virtual Keyboard**
- **Word Prediction**: word prediction mechanism based on the LSTM neural network model
- **Text-to-Speech**: Read written text aloud using the Yapper TTS engine
- **Text Management**: Save and load written text to/from files

## Requirements

### System Requirements
- **Operating System**: Linux (tested on Linux systems)
- **Python**: min. python 3.10; max. python 3.13
- **Dependencies**: see `requirements.txt` for full list

## Installation

Use the provided installation script:

```bash
chmod +x instaluj.sh
./instaluj.sh
```

The script will:
1. Clone or update the repository
2. Create a Python virtual environment
3. Install all required dependencies
4. Create a desktop icon for easy access
