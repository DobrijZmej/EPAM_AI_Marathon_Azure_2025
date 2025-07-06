# Function App Terraform Module

Цей модуль створює Azure Function App (Python), окремий Storage Account для функції, Application Insights та Consumption Plan.

## Вхідні змінні
- `resource_group_name`
- `location`
- `function_app_name`
- `storage_account_name` (для функції)
- `app_insights_name`
- `app_settings` (map, для environment variables)

## Outputs
- `function_app_name`
- `function_app_default_hostname`
- `function_app_id`
- `app_insights_instrumentation_key`

## Примітки
- Consumption Plan (Y1) — мінімальні витрати
- Storage Account для функції створюється окремо
- Application Insights підключено автоматично
