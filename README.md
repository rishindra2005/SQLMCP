# DBMS MCP Agent

This project implements a ReAct-style agent for advanced database management. The agent is powered by Google's Gemini model and equipped with a comprehensive suite of tools (`FastMCP`) to interact with, manage, and analyze MySQL databases.

The agent provides an interactive command-line client (`test_client.py`) that allows users to issue natural language commands to perform complex database operations.

## Features

The agent's capabilities are organized into several categories:

- **Connection Management**: Connect to different databases and manage the active connection.
- **Discovery & Metadata**: List databases and tables, and retrieve detailed schema information, including table structures, relations, indexes, and views. Includes a high-level tool to get the entire database schema at once.
- **Data Management**: Perform CRUD operations (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) on database records, with support for both single and bulk operations.
- **Schema Engineering**: Create and drop tables, add columns, and manage indexes.
- **Transaction & Integrity**: Execute multiple queries in a single atomic transaction and check for data integrity issues like orphaned records and constraint violations.
- **Performance & Admin**: Analyze query performance with `EXPLAIN`, view database statistics, and list active server processes.
- **Visualization**: Generate detailed, interactive ER diagrams and schema documentation using SchemaSpy, which can be viewed directly in a browser.

A full list of tools and their documentation can be found in [tools.md](tools.md).

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- Python 3.8+
- A running MySQL server
- Java (for the SchemaSpy visualization tool)
- Graphviz (a dependency for SchemaSpy, installable via `sudo apt-get install graphviz` on Debian/Ubuntu)

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Python dependencies:**
    A `requirements.txt` file is not yet available. Install the required packages manually:
    ```bash
    pip install "fastmcp @ git+https://github.com/google/generative-ai-docs@main#subdirectory=examples/gemini/python/tools/fastmcp"
    pip install sqlalchemy mysql-connector-python python-dotenv pandas eralchemy2
    ```

4.  **Configure Environment Variables:**
    - Create a file named `.env` in the project root.
    - Add your Gemini API key to this file:
      ```
      GEMINI_API_KEY="YOUR_API_KEY_HERE"
      ```
    - The database connection is currently hardcoded in `main.py` and `test_db.py` to connect as user `rishi` to `localhost:3306`. You may need to modify the `create_engine` calls in these files to match your MySQL setup.

5.  **Download Visualization Tools:**
    The visualization tool requires `SchemaSpy` and a JDBC driver. The test suite will download these for you automatically when it runs for the first time. To trigger this, you can run the tests as described below.

## Usage

The application consists of two main components: the MCP server that exposes the tools, and the interactive client that you use to talk to the agent.

1.  **Start the MCP Server:**
    Open a terminal and run the following command from the project root:
    ```bash
    python main.py
    ```
    The server will start and be ready to accept tool calls from the agent.

2.  **Run the Interactive Client:**
    Open a *second* terminal and run the client:
    ```bash
    python test_client.py
    ```
    You will be prompted with `>`. You can now type commands in natural language, like "list all databases" or "show me the schema for the users table".

## Running Tests

A test suite is provided in `test_db.py` to verify the functionality of all database tools. To run it:

```bash
python test_db.py
```
This will create a temporary test database, run a series of tests against all tools (including the visualization tool), and then clean up the test database.
