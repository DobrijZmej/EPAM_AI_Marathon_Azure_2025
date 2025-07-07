resource "azurerm_monitor_workbook" "dialog_analytics" {
  name                = "neurodialog-analytics"
  resource_group_name = var.resource_group_name
  location            = var.location
  display_name        = "Dialog Analytics (Sentiment & Topics)"
  data_json           = <<JSON
{
  "version": "Notebook/1.0",
  "items": [
    {
      "type": 1,
      "content": {
        "json": "## Dialog Analytics Dashboard\nThis workbook visualizes AI dialog data from Cosmos DB."
      }
    },
    {
      "type": 3,
      "content": {
        "chartType": "pie",
        "title": "Questions by Language / Кількість запитань за мовами",
        "query": "SELECT c.meta.lang, COUNT(1) AS count FROM c WHERE IS_DEFINED(c.meta.lang) GROUP BY c.meta.lang ORDER BY count DESC",
        "dataSource": "CosmosDB"
      }
    },
    {
      "type": 3,
      "content": {
        "chartType": "pie",
        "title": "Sentiment Distribution / Розподіл тональності",
        "query": "SELECT c.meta.sentiment, COUNT(1) AS count FROM c WHERE IS_DEFINED(c.meta.sentiment) GROUP BY c.meta.sentiment ORDER BY count DESC",
        "dataSource": "CosmosDB"
      }
    },
    {
      "type": 3,
      "content": {
        "chartType": "table",
        "title": "Top Key Phrases / Найчастіші ключові фрази",
        "query": "SELECT phrase, COUNT(1) AS count FROM c JOIN phrase IN c.meta.key_phrases WHERE IS_DEFINED(c.meta.key_phrases) GROUP BY phrase ORDER BY count DESC OFFSET 0 LIMIT 10",
        "dataSource": "CosmosDB"
      }
    },
    {
      "type": 3,
      "content": {
        "chartType": "timechart",
        "title": "Dialogs in Last 24h / Діалоги за 24 години",
        "query": "SELECT VALUE COUNT(1) FROM c WHERE c._ts > (GetCurrentEpochTime() - 86400)",
        "dataSource": "CosmosDB"
      }
    },
    {
      "type": 3,
      "content": {
        "chartType": "table",
        "title": "Dialogs by User / Діалоги по користувачах",
        "query": "SELECT c.user_id, COUNT(1) AS count FROM c WHERE IS_DEFINED(c.user_id) GROUP BY c.user_id ORDER BY count DESC OFFSET 0 LIMIT 10",
        "dataSource": "CosmosDB"
      }
    }
  ]
}
JSON
}
