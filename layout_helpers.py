
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc



def gen_navbar(brand, items,
    barClass='navbar-dark bg-dark p-1',
    #brandClass='col-sm-3 col-md-2 mr-0',
    listClass='px-3',
    itemLiClass='text-nowrap',
    itemAClass='',
    dark=True,
    color='dark'):
    return dbc.NavbarSimple(
        [
            dbc.NavItem(
                dbc.NavLink(key, href=items[key], className=itemAClass),
                className=itemLiClass
            )
            for key in items
        ],
        brand=brand,
        dark=dark,
        color=color,
        className=barClass
    )


def gen_sidebar_layout(sidebar, content, sidebar_size=2,
    sidebarClass='bg-light', contentClass='', mainClass=''):
    return dbc.Row([
        dbc.Col(sidebar, className=f"sidebar {sidebarClass}", width=sidebar_size),
        dbc.Col(content, size=12-sidebar_size, className=contentClass)
    ], className="mainClass")



def gen_grid(items, gridClass='', colClass='', rowClass=''):
    rows = []
    for row in items:
        cols = []
        size = int(12 / len(row))
        for col in row:
            cols.append(dbc.Col(col, className=colClass))
        rows.append(dbc.Row(cols, className=rowClass))
    return html.Div(rows, className=gridClass)


def gen_card(text, id=None, title='', cardClass='border-light', 
             textClass='text-center', titleClass='text-center'):
    return dbc.Card(
        dbc.CardBody([
            html.H5(title, className=f'card-title {titleClass}'),
            html.P(text, id=id, className=f'card-text {textClass}')
        ]),
        className=cardClass
    )
