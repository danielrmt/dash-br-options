
import dash_core_components as dcc
import dash_html_components as html



def gen_navbar(brand, items,
    barClass='navbar-dark bg-dark p-1',
    brandClass='col-sm-3 col-md-2 mr-0',
    listClass='px-3',
    itemLiClass='text-nowrap',
    itemAClass=''):
    item_list = []
    for key in items:
        item_list.append(
            html.Li(
                html.A(key, href=items[key],
                    className=f"nav-link {itemAClass}"),
                className=f"nav-item {itemLiClass}"
            )
        )
    return html.Nav(
        [
            html.A(brand, className=f"navbar-brand {brandClass}"),
            html.Ul(item_list, className=f"navbar-nav {listClass}")
        ], className=f"navbar {barClass}"
    )



def gen_sidebar_layout(sidebar, content, sidebar_size=2,
    sidebarClass='bg-light p-5', contentClass='', mainClass=''):
    return html.Div(
        [html.Div(sidebar, className=f"sidebar col-md-{sidebar_size} {sidebarClass}"),
         html.Div(content, className=f"col-md-{12-sidebar_size} {contentClass}")],
        className=f"row {mainClass}"
    )



def gen_grid(items, gridClass='', colClass='', rowClass=''):
    rows = []
    for row in items:
        cols = []
        size = int(12 / len(row))
        for col in row:
            cols.append(html.Div(col, className=f"col-md-{size} {colClass}"))
        rows.append(html.Div(cols, className=f"row {rowClass}"))
    return html.Div(rows, className=f"{gridClass}")



def gen_card(text, id=None, title='', cardClass='border-light', 
             textClass='text-center', titleClass='text-center'):
    return html.Div([
        html.Div([
            html.H5(title, className=f'card-title {titleClass}'),
            html.P(text, id=id, className=f'card-text {textClass}')
        ], className='card-body')
    ], className=f'card {cardClass}')

