### ⚠️ Work in Progress

#### You can find the English version of this README below.

---

# O projekcie

To repozytorium zawiera **środowisko symulujące prostą aplikację do alternatywnej komunikacji (AAC)**, stworzone na potrzeby pracy magisterskiej.
Celem projektu jest przeprowadzenie eksperymentu badającego wykorzystanie modeli predykcyjnych (sieć LSTM) w aplikacjach AAC opartych o interfejs skanujący (switch-scanning).

Projekt czerpie inspirację z architektury i rozwiązań zastosowanych w aplikacji [**PISAK**](https://github.com/BrainTech/pisak), nie jest jednak jej nową wersją ani kontynuacją — to odrębne, eksperymentalne narzędzie badawcze przygotowane na potrzeby konkretnego eksperymentu.

## Funkcje

### Moduł Speller
Aktualnie jedynym modułem uruchamianym w ramach eksperymentu jest **Speller**, który umożliwia komunikację za pomocą wirtualnej klawiatury:
- **Interfejs skanujący (switch-scanning)**: nawigacja po elementach interfejsu za pomocą urządzenia przełącznikowego
- **Wirtualna klawiatura**
- **Predykcja słów**: predykcje kolejnych słów generowane z wykorzystaniem modelu LSTM (model do użycia można wskazać przy uruchomieniu)
- **Text-to-Speech**: odczytywanie wpisanego tekstu przy użyciu silnika Yapper TTS
- **Zarządzanie tekstem**: zapisywanie i wczytywanie tekstu z plików
- **Logowanie przebiegu eksperymentu**: zdarzenia z sesji zapisywane są do pliku CSV dla każdego uczestnika, modelu i uruchomienia

> W kodzie znajdują się też moduły `main_menu` i `symboler` — są to elementy w trakcie tworzenia, niepodpięte jeszcze pod główny sposób uruchamiania aplikacji (`start_app`) i niewykorzystywane w eksperymencie.

## Uruchamianie eksperymentu

Aplikację uruchamia się poleceniem `start_app` (patrz sekcja [Instalacja](#instalacja)), które przyjmuje następujące argumenty:

| Argument | Opis | Domyślna wartość |
|---|---|---|
| `-m`, `--model` | nazwa pliku modelu predykcyjnego z katalogu `app/predictions` | `model.pt` |
| `-p`, `--participant` | nazwa/identyfikator uczestnika eksperymentu | `experiment` |

Przykład:
```bash
start_app --model fine_tuned_model.pt --participant P01
```

Logi aplikacji zapisywane są w `~/aac_app/logs`, a dane z eksperymentu (w formacie CSV, osobno dla każdego uczestnika, modelu i sesji) w `~/aac_app/experiment`.

## Wymagania

### Wymagania systemowe
- **System operacyjny**: Linux (testowane na dystrybucjach Linux)
- **Python**: min. python 3.10; max. python 3.13
- **Wymagane pakiety**: pełna lista w `requirements.txt`

## Instalacja

Aby zainstalować aplikację, należy pobrać plik [`instaluj.sh`](https://github.com/Julia-M-B/master_thesis_app/blob/main/instaluj.sh), a następnie
uruchomić go, korzystając z komendy:

```bash
chmod +x instaluj.sh
./instaluj.sh
```

Skrypt wykona następujące czynności:
1. Sklonuje lub zaktualizuje repozytorium (do katalogu `~/aac_experiment`)
2. Utworzy wirtualne środowisko Python
3. Zainstaluje wszystkie wymagane zależności
4. Utworzy ikonę na pulpicie dla łatwego dostępu

---
# English version

# About the project

This repository contains an **experimental environment simulating a simple augmentative and alternative communication (AAC) application**, created for the purposes of a master's thesis.
The goal of the project is to run an experiment studying the use of predictive models (an LSTM network) in AAC applications based on a switch-scanning interface.

The project draws inspiration from the architecture and solutions used in the [**PISAK**](https://github.com/BrainTech/pisak) application, but it is not a new version of it nor a continuation — it is a separate, experimental research tool built for a specific experiment.

## Features

### Speller module
Currently the only module launched as part of the experiment is **Speller**, which enables communication through a virtual keyboard:
- **Switch-Scanning Interface**: navigate through UI elements using a single switch
- **Virtual Keyboard**
- **Word Prediction**: word prediction mechanism based on an LSTM neural network model (the model to use can be selected at startup)
- **Text-to-Speech**: read written text aloud using the Yapper TTS engine
- **Text Management**: save and load written text to/from files
- **Experiment logging**: session events are logged to a CSV file per participant, model, and run

> The codebase also contains `main_menu` and `symboler` modules — these are still under development, not yet wired into the main entry point (`start_app`), and are not used in the experiment.

## Running the experiment

The application is launched with the `start_app` command (see [Installation](#installation)), which accepts the following arguments:

| Argument | Description | Default |
|---|---|---|
| `-m`, `--model` | prediction model filename from the `app/predictions` directory | `model.pt` |
| `-p`, `--participant` | name/identifier of the experiment participant | `experiment` |

Example:
```bash
start_app --model fine_tuned_model.pt --participant P01
```

Application logs are written to `~/aac_app/logs`, and experiment data (CSV format, separate per participant, model, and session) to `~/aac_app/experiment`.

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
1. Clone or update the repository (into `~/aac_experiment`)
2. Create a Python virtual environment
3. Install all required dependencies
4. Create a desktop icon for easy access
