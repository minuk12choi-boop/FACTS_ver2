from .history import history_view
from .prevent_tip import prevent_tip_view, prevent_tip_data_api
from .master import master_view
from .kpi import kpi_view

from .dashboard.page import dashboard_view
from .dashboard.data_api import dashboard_data_api, dashboard_prp_options_api
from .dashboard.override_api import (
    dashboard_override_detail_api,
    dashboard_override_save_api,
    dashboard_override_member_save_api,
)
from .dashboard.plan_api import (
    dashboard_plan_detail_api,
    dashboard_plan_save_api,
    dashboard_plan_delete_api,
)
from .dashboard.tip_missing_api import (
    dashboard_tip_missing_detail_api,
    dashboard_tip_missing_save_api,
    dashboard_tip_missing_delete_api,
)
from .dashboard.similar_eqp_api import dashboard_similar_eqp_api
from .dashboard.bulk_upload_api import dashboard_bulk_upload_api, dashboard_upload_template
from .dashboard.export_api import prp_export_csv, prp_export_csv_all
