# Story Protocol Plugin

<details>
<summary>Table of Contents</summary>

- [Story Protocol Plugin](#story-protocol-plugin)
  - [Overview](#overview)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Functions](#functions)
  - [Useful Resources](#useful-resources)

</details>

---

> **Note:** This plugin is currently in development. Features and documentation may change in upcoming releases.

The Story Protocol plugin provides integration with Story Protocol's API for managing digital assets and their metadata on the blockchain. This plugin allows you to:

1. Retrieve asset information from Story Protocol
2. Access asset metadata
3. Interact with the Story Protocol ecosystem

## Installation

From this directory (`story_protocol`), run the installation:

```bash
poetry install
```

## Usage

1. Activate the virtual environment by running:

```bash
eval $(poetry env activate)
```

2. Import story_protocol_plugin by running:

```python
from story_protocol.story_protocol_plugin import StoryProtocol
```

3. Create and initialize an Story Protocol instance by running:

```python
story_protocol = StoryProtocol(
    api_key="your_api_key_here",
    chain="your_chain_here"
)
```

4. Use the Story Protocol instance to interact with the Story Protocol API.

## Functions

### get_asset

```python
asset_info = story_protocol.get_asset(asset_id)
```

### get_metadata

```python
metadata = story_protocol.get_metadata(asset_id)
```
