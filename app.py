import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import pandas as pd
import ast
from datetime import datetime
import plotly.express as px
from dash.dependencies import Input, Output
import math
import os
import time
import logging

logging.basicConfig(level=logging.DEBUG)
def print(*messages):
    logging.info(' '.join(map(str, messages)))

def wait_for_file(filepath, timeout=500):
    """
    Wait for a file to appear at the given filepath. 
    If the file does not appear within the timeout period, raise an exception.
    """
    start_time = time.time()
    while not os.path.exists(filepath):
        time.sleep(1)
        if time.time() - start_time > timeout:
            raise FileNotFoundError(f"{filepath} not found after {timeout} seconds")
    print(f"{filepath} found!")
    # Continue with the rest of your code

# usage
wait_for_file(f'{os.getcwd()}/outputs/data_filtered.xlsx')

# Initialisation de l'application Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Ici, chargez votre DataFrame
df = pd.read_excel("./outputs/data_filtered.xlsx")

# Conversion des coordonnées de chaîne à liste
df['Coordonnées'] = df['Coordonnées'].apply(ast.literal_eval)

markers = [dl.Marker(position=coord, children=[
    dl.Tooltip("Lieu de collecte: {}".format(place)),
    dl.Popup([
        html.H1("Coordonnées"),
        html.P("Latitude: {}".format(coord[0])),
        html.P("Longitude: {}".format(coord[1]))
    ])
]) for coord, place in zip(df['Coordonnées'], df['Lieu de collecte'])]

# Filtres
filters = html.Div([
    dcc.Dropdown(
        id='type-prestation-dropdown',
        options=[{'label': i, 'value': i} for i in df['Type de prestation'].unique()],
        placeholder="Type de prestation...",
    ),
    dcc.Dropdown(
        id='etat-realisation-dropdown',
        options=[{'label': i, 'value': i} for i in df['Etat de réalisation'].unique()],
        placeholder="Etat de réalisation...",
    ),
    dcc.Dropdown(
        id='etat-facturation-dropdown',
        options=[{'label': i, 'value': i} for i in df['Etat de facturation'].unique()],
        placeholder="Etat de facturation...",
    )
], style={'display': 'flex', 'flex-direction': 'row', 'gap': '10px'})

# Header avec logo et filtres à droite
header = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(html.Img(src="https://takeawaste.fr/wp-content/uploads/2020/10/2019_03_TAW_Logotype_sans_baseline_couleur_fond_transparent_HD_RVB.png", className="logo"), width=6),
                    dbc.Col(filters, width=6),
                ],
                align="between"
            ),
        ],
        fluid=True,
    ),
    color="white",
)

# Map
map_ = html.Div([
    dl.Map([
        dl.TileLayer(),
        dl.MarkerClusterGroup(children=markers)
    ], style={'width': '100%', 'height': '100vh'}, center=[46.603354, 1.888334], zoom=6,
    maxBounds=[[41, -5.266007], [51, 9.662499]],  # Limites de déplacement de la carte
    maxBoundsViscosity=1.0, id="map-container")  # Force à rester dans les limites
], style={'width': '45vw', 'height': '100vh'})

# Bar chart
df['Matière'] = df['Matière'].fillna('Inconnu')
fig = px.bar(df['Matière'].value_counts().reset_index(), x='Matière', y='index', title="Répartition par matière", orientation='h')

bar_chart = dcc.Graph(
    id='graph',
    figure=fig
)

df['Heure de réalisation'] = pd.to_datetime(df['Heure de réalisation'])

with open("./last_update.txt", 'r') as f:
    last_update = f.read()

# Info box
info_box = dbc.Row([
    dbc.Row([
        dbc.Col([
            html.H2("Dernière actualisation :"),
            html.H3("{}".format(last_update)),
        ], style={'padding': '10px', 'margin': '10px', "background-image":'url("https://takeawaste.fr/wp-content/uploads/2022/08/Fond-web-site.png")', 'background-size': 'cover', 'background-repeat': 'no-repeat', "border-radius":"10px"})
    ],style={'display': 'flex', "flex-direction": "row"}),
    dbc.Row([
        dbc.Col([
            html.H2("Nombre de lignes"),
            html.H3("{}".format(df.shape[0]), id="nb_lignes"),
        ], style={'padding': '10px', 'margin': '10px',"background-image":'url("https://takeawaste.fr/wp-content/uploads/2022/08/Fond-web-site.png")', 'background-size': 'cover', 'background-repeat': 'no-repeat', "border-radius":"10px"}),
        dbc.Col([
            html.H2("Heure moyenne de réalisation"),
            html.H3("{}".format(int(df['Heure de réalisation'].dt.hour.mean())), id="heure_moy"),
        ], style={'padding': '10px', 'margin': '10px', "background-image":'url("https://takeawaste.fr/wp-content/uploads/2022/08/Fond-web-site.png")', 'background-size': 'cover', 'background-repeat': 'no-repeat', "border-radius":"10px"}),
    ],style={'display': 'flex', "flex-direction": "row"}),
    dbc.Col([
        bar_chart
    ], style={'width': '100%'})
], style={'width': '100%', 'height': '100vh', 'display': 'flex', 'align-items': 'center', "flex-direction": "column"})

# Création du layout de l'application
app.layout = html.Div([
    header,
    dbc.Row([
        dbc.Col(map_, style={'padding': 0}),
        dbc.Col(info_box, style={'padding': 0})
    ])
])

@app.callback(
    [Output('map-container', 'children'),
     Output('graph', 'figure'),
     Output('nb_lignes', 'children'),
     Output('heure_moy', 'children')],
    [Input('type-prestation-dropdown', 'value'),
     Input('etat-realisation-dropdown', 'value'),
     Input('etat-facturation-dropdown', 'value')]
)
def update_output(type_prestation, etat_realisation, etat_facturation):
    df_filtered = df

    if type_prestation:
        df_filtered = df_filtered[df_filtered['Type de prestation'] == type_prestation]

    if etat_realisation:
        df_filtered = df_filtered[df_filtered['Etat de réalisation'] == etat_realisation]

    if etat_facturation:
        df_filtered = df_filtered[df_filtered['Etat de facturation'] == etat_facturation]
    
    if df_filtered.empty:
        # Si le DataFrame filtré est vide, créez une carte vide et renvoyez zéro pour les autres valeurs
        map_ = dl.Map([
            dl.TileLayer()
        ], style={'width': '100%', 'height': '100vh'}, center=[46.603354, 1.888334], zoom=6,
        maxBounds=[[41, -5.266007], [51, 9.662499]],  # Limites de déplacement de la carte
        maxBoundsViscosity=1.0, id="map")  # Force à rester dans les limites

        fig = px.bar(title="Répartition par matière", orientation='h')

        return map_, fig, 0, 0

    markers = [dl.Marker(position=coord, children=[
        dl.Tooltip("Lieu de collecte: {}".format(place)),
        dl.Popup([
            html.H1("Coordonnées"),
            html.P("Latitude: {}".format(coord[0])),
            html.P("Longitude: {}".format(coord[1]))
        ])
    ]) for coord, place in zip(df_filtered['Coordonnées'], df_filtered['Lieu de collecte'])]

    map_ = dl.Map([
        dl.TileLayer(),
        dl.MarkerClusterGroup(children=markers)
    ], style={'width': '100%', 'height': '100vh'}, center=[46.603354, 1.888334], zoom=6,
    maxBounds=[[41, -5.266007], [51, 9.662499]],  # Limites de déplacement de la carte
    maxBoundsViscosity=1.0, id="map")  # Force à rester dans les limites

    fig = px.bar(df_filtered['Matière'].value_counts().reset_index(), x='Matière', y='index', title="Répartition par matière", orientation='h')

    nb_lignes = df_filtered.shape[0]
    if not math.isnan(df_filtered['Heure de réalisation'].dt.hour.mean()) :
        heure_moy = int(df_filtered['Heure de réalisation'].dt.hour.mean())
    else :
        heure_moy = 0
    

    return map_, fig, nb_lignes, heure_moy

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')