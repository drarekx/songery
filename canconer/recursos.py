"""Cançoners base: reculls de cançons de domini públic que es poden crear des de la pàgina d'inici.

Només hi van cançons tradicionals o d'autors morts fa més de 80 anys. Els acords són una
harmonització senzilla per a guitarra.
"""

from __future__ import annotations

from . import basedades, document

NADALES = [
    {"titol": "El cant dels ocells", "autor": "Popular catalana", "cos": """\
[Intro]
Am  E  Am

Am          E
Al veure despuntar
            Am
el major lluminar
Dm         Am      E
en la nit més ditxosa,
Am           E
els ocellets cantant
           Am
a festejar-lo van
Dm        E        Am
amb sa veu melindrosa.

Am          E
L'àliga imperial
            Am
pels aires va volant
Dm        Am       E
cantant amb melodia,
Am          E
dient: Jesús és nat
           Am
per treure'ns del pecat
Dm       E        Am
i dar-nos alegria."""},
    {"titol": "Fum, fum, fum", "autor": "Popular catalana", "cos": """\
Dm                 A
A vint-i-cinc de desembre,
Dm      A   Dm
fum, fum, fum.
Dm                 A
A vint-i-cinc de desembre,
Dm      A   Dm
fum, fum, fum.
F               C
Ha nascut un minyonet
          F      C       F
ros i blanquet, ros i blanquet;
Dm              A
fill de la Verge Maria,
Dm               A
n'és nat en una establia,
Dm      A   Dm
fum, fum, fum.

Dm                 A
Allà dalt de la muntanya,
Dm      A   Dm
fum, fum, fum.
Dm                 A
Allà dalt de la muntanya,
Dm      A   Dm
fum, fum, fum.
F               C
Si n'hi ha dos pastorets
           F       C        F
abrigadets, abrigadets,
Dm              A
amb la pell i la samarra,
Dm               A
menjant ous i botifarra,
Dm      A   Dm
fum, fum, fum."""},
    {"titol": "El noi de la mare", "autor": "Popular catalana", "cos": """\
D                    A
Què li darem a n'el Noi de la Mare?
A                    D
Què li darem que li sàpiga bo?
D            G       D
Panses i figues i nous i olives,
G           D    A      D
panses i figues i mel i mató."""},
    {"titol": "El desembre congelat", "autor": "Popular catalana", "cos": """\
G              D
El desembre congelat
G         D
confús es retira;
G            C
abril, de flors coronat,
G       D     G
tot el món admira.
C               G
Quan en un jardí d'amor
D               G
neix una divina flor,
G
d'una ro, ro, ro,
D
d'una sa, sa, sa,
G             D
d'una ro, d'una sa,
G          C
d'una rosa bella,
G       D      G
fecunda i poncella.

G              D
El primer pare causà
G         D
la nit tenebrosa
G            C
que a tot el món ofuscà
G       D     G
la vista penosa;
C               G
mes en una mitjanit
D               G
brilla el sol que n'és eixit
G
d'una be, be, be,
D
d'una lla, lla, lla,
G             D
d'una be, d'una lla,
G          C
d'una bella aurora
G       D      G
que el cel enamora."""},
    {"titol": "Caga tió", "autor": "Popular catalana", "cos": """\
C                 G
Caga tió, ametlles i torró,
C                    G
no caguis arengades, que són massa salades,
C          G       C
caga torrons, que són més bons."""},
    {"titol": "Adeste fideles", "autor": "Tradicional (llatí)", "cos": """\
G       D    G     C   G   D
Adeste fideles, laeti triumphantes,
Em  D   A7    D    G   A   D
venite, venite in Bethlehem.
G         C     G    D
Natum videte regem angelorum.

[Tornada]
G                 D
Venite adoremus,
G                 D
venite adoremus,
Em    D  C    G  C  G  D  G
venite adoremus Dominum."""},
]

POPULARS = [
    {"titol": "Els segadors", "autor": "Popular · lletra d'Emili Guanyavents", "cos": """\
Dm                 A7
Catalunya triomfant
                   Dm
tornarà a ser rica i plena.
Dm                 A7
Endarrere aquesta gent
                   Dm
tan ufana i tan superba.

[Tornada]
F            C
Bon cop de falç!
A7                            Dm
Bon cop de falç, defensors de la terra!
F            C   A7  Dm
Bon cop de falç!

Dm                 A7
Ara és hora, segadors,
                   Dm
ara és hora d'estar alerta.
Dm                 A7
Per quan vingui un altre juny
                   Dm
esmolem ben bé les eines.

[Tornada]

Dm                 A7
Que tremoli l'enemic
                   Dm
en veient la nostra ensenya:
Dm                 A7
com fem caure espigues d'or,
                   Dm
quan convé seguem cadenes.

[Tornada]"""},
    {"titol": "La Balanguera", "autor": "Joan Alcover · Amadeu Vives", "cos": """\
Am              E
La Balanguera misteriosa,
E7              Am
com una aranya d'art subtil,
Am              Dm
buida que buida la filosa,
E               Am
de nostra vida treu lo fil.
C               G
Com una parca, bé cavil·la
G7              C
teixint la tela per demà.
F            C       E      Am
La Balanguera fila, fila,
Dm         E     Am
la Balanguera filarà."""},
    {"titol": "La Santa Espina", "autor": "Àngel Guimerà · Enric Morera", "cos": """\
C                 G
Som i serem gent catalana
G7                C
tant si es vol com si no es vol,
C               F
que no hi ha terra més ufana
C       G         C
sota la capa del sol.
F                 C
Déu va passar-hi en primavera,
G                 C
i tot cantava al seu pas.
F                 C
Canta la terra encara entera,
G                 C
i canta que cantaràs."""},
    {"titol": "El rossinyol", "autor": "Popular catalana", "cos": """\
G                D
Rossinyol, que vas a França,
       G
rossinyol,
               D
encomana'm a la mare,
       G
rossinyol,
C           G
d'un bell bocatge,
D        G
rossinyol d'un vol.

G                D
Encomana'm a la mare,
       G
rossinyol,
               D
i a mon pare no,
       G
rossinyol,
C           G
d'un bell bocatge,
D        G
rossinyol d'un vol."""},
    {"titol": "El gegant del Pi", "autor": "Popular catalana", "cos": """\
D                 A
El gegant del Pi ara balla, ara balla,
A                 D
el gegant del Pi ara balla pel camí.

D                       A
El gegant de la ciutat ara balla, ara balla,
A                       D
el gegant de la ciutat ara balla pel terrat."""},
    {"titol": "Plou i fa sol", "autor": "Popular catalana", "cos": """\
C          G
Plou i fa sol,
G                 C
les bruixes es pentinen,
C          G
plou i fa sol,
G               C
les bruixes fan un ou."""},
    {"titol": "Cargol treu banya", "autor": "Popular catalana", "cos": """\
D                A
Cargol, treu banya,
A                 D
puja a la muntanya,
D             A
cargol bover,
A              D
puja al teu paper."""},
]

BASES = {
    "nadales": {
        "titol": "Nadales", "subtitol": "Cançons de Nadal tradicionals",
        "descripcio": "Nadales tradicionals catalanes", "cancons": NADALES,
    },
    "populars": {
        "titol": "Cançons populars", "subtitol": "Repertori tradicional català",
        "descripcio": "Cançons populars i tradicionals", "cancons": POPULARS,
    },
}


def crea(clau: str) -> str:
    """Crea el cançoner base `clau` amb les seves cançons (noves a la biblioteca) i en retorna l'id."""
    base = BASES[clau]
    id_canconer = basedades.crea_canconer(base["titol"], subtitol=base["subtitol"],
                                          contraportada="Cançons de domini públic.\nBona cantada!")
    for c in base["cancons"]:
        id_canco = basedades.crea_canco(c["titol"], c["autor"], document.de_text(c["cos"]))
        basedades.crea_versio(id_canco, "Versió inicial")
        basedades.afegeix_entrada(id_canconer, id_canco)
    return id_canconer
