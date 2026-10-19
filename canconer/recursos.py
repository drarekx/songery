"""Cançoners base: reculls de cançons de domini públic que es poden crear des de la pàgina d'inici.

Només hi van cançons tradicionals o d'autors morts fa més de 80 anys. Les lletres i els acords
(per a guitarra) estan contrastats amb fonts: vegeu el comentari de cada recull.
"""

from __future__ import annotations

from . import basedades, document, plantilles

# Lletres i acords contrastats sobretot amb «Cançons populars i tradicionals a l'escola» (Generalitat),
# que porta els acords sobre la partitura, i amb Viquitexts, la Viquipèdia i reculls d'acords.
# Caga tió és una cantarella: els acords de la versió curta només tenen una font.
NADALES = [
    {"titol": "El cant dels ocells", "autor": "Popular catalana", "cos": """\
   Em
En veure despuntar
   B7         Em
el major lluminar,
   F#           B7
en la nit més joiosa,
E                Am
els ocellets, cantant,
  D7          G
a festejar-lo van
       F#       B7 Em
amb sa veu melindrosa. (bis)

   Em
L'àliga imperial
     B7         Em
pels aires va volant,
   F#           B7
cantant amb melodia,
E               Am
dient: Jesús és nat
    D7             G
per treure'ns de pecat
      F#     B7 Em
i dar-nos alegria. (bis)

   Em
Respon-li lo pardal:
 B7            Em
Avui, nit de Nadal,
   F#             B7 Em
és nit de gran contento!
E                 Am
El verdum i el lluer
   D7             G
diuen cantant, també:
       F#         B7 Em
Oh, quina alegria sento! (bis)"""},
    {"titol": "Fum, fum, fum", "autor": "Popular catalana", "cos": """\
Am            E
A vint-i-cinc de desembre,
Am   E7   Am
fum, fum, fum;
Am            E
a vint-i-cinc de desembre,
Am   E7   Am
fum, fum, fum.
G     C      G7   C
Ha nascut un minyonet
    G7    C         G7    C
ros i blanquet, ros i blanquet,
        Dm         E
fill de la Verge Maria,
Am       Dm         E
n'és nat en una establia,
Am   E7   Am
fum, fum, fum.

Am           E
Allà dalt de la muntanya,
Am   E7   Am
fum, fum, fum;
Am           E
allà dalt de la muntanya,
Am   E7   Am
fum, fum, fum.
G       C      G7   C
Si n'hi ha dos pastorets
 G7   C      G7   C
abrigadets, abrigadets,
       Dm          E
amb la pell i la samarra
Am     Dm        E
mengen ous i botifarra,
Am   E7   Am
fum, fum, fum.

Am              E
Qui en dirà més gran mentida?,
Am   E7   Am
fum, fum, fum;
Am              E
qui en dirà més gran mentida?,
Am   E7   Am
fum, fum, fum.
G        C      G7  C
Ja en respon el majoral,
    G7     C        G7     C
amb gran cabal, amb gran cabal:
        Dm           E
Jo en faré deu mil camades
Am     Dm            E
amb un salt totes plegades,
Am   E7   Am
fum, fum, fum."""},
    {"titol": "El noi de la mare", "autor": "Popular catalana", "cos": """\
D                   G
Què li darem a n'el Noi de la Mare?
D                   G      D
Què li darem que li sàpiga bo?
                  A7      D
Panses i figues i nous i olives,
                  A7      D
panses i figues i mel i mató.

D                 G
Què li darem al Fillet de Maria?
D                  G        D
Què li darem al formós Infantó?
                    A7     D
Li darem panses amb unes balances,
                    A7     D
li darem figues amb un paneró.

D                      G
Tam, patantam, que les figues són verdes;
D                     G     D
tam, patantam, que ja maduraran.
                 A7     D
Si no maduren el dia de Pasqua,
                A7      D
maduraran en el dia del Ram."""},
    {"titol": "El desembre congelat", "autor": "Popular catalana", "cos": """\
     D
El desembre congelat
       G    A7 D
confús es retira.
                    D
Abril, de flors coronat,
       G     A7 D
tot el món admira.
        G           D
Quan en un jardí d'amor
      G         D
neix una divina flor,
d'una ro, ro, ro,
d'una sa, sa, sa,
d'una ro, d'una sa,
d'una rosa bella,
D7   G       A7 D
fecunda i poncella.

      D
El primer pare causà
       G   A7 D
la nit tenebrosa
                     D
que a tot el món ofuscà
      G    A7 D
la vista penosa;
        G        D
mes, en una mitjanit,
          G              D
brilla el sol que n'és eixit
d'una be, be, be,
d'una lla, lla, lla,
d'una be, d'una lla,
d'una bella aurora
D7         G  A7 D
que el cel enamora.

    D
Arribaren els tres Reis
       G     A7 D
amb molta alegria,
                   D
adorant el Rei del Cel
    G      A7 D
en una establia.
   G               D
Oferint-li tres presents,
        G             D
com són or, mirra i encens.
A la Ma, Ma, Ma,
a la re, re, re,
a la Ma, a la re,
a la Mare pia,
D7    G    A7 D
la Verge Maria."""},
    {"titol": "Caga tió", "autor": "Popular catalana", "cos": """\
D    G    D            G
Caga tió, ametlles i torró,
   G          C          D           G
no caguis arengades, que són massa salades,
G      C          D       G
caga torrons, que són més bons.

G
Caga tió, tió de Nadal;
posarem el porc en sal,
la gallina a la pastera
i el pollí a dalt del pi.
Toca, toca, Valentí.
Passen bous i vaques,
gallines amb sabates
i galls amb sabatons.
Correu, correu, minyons,
que la teta fa torrons,
el vicari els ha tastats,
diu que són un poc salats.
Ai, el brut; ai, el porc;
ai, el cara, cara, cara;
ai, el brut; ai, el porc;
ai, el cara de pebrot."""},
    {"titol": "Adeste fideles", "autor": "Tradicional (llatí) · atribuït a John Francis Wade", "cos": """\
G        Am D   G  D  G  C G   D
Adeste fideles, laeti triumphantes,
Em  D   A D    G  D   A7 D
venite, venite in Bethlehem.
G       D7 G  D G   Em Am D
Natum videte, Regem angelorum.

[Tornada]
G       D7 G
Venite adoremus,
G       D7 G D
venite adoremus,
G   D   A7 D G
venite adoremus
G D7 G
Dominum.

Cantet nunc io chorus angelorum,
cantet nunc aula caelestium:
Gloria, gloria in excelsis Deo!

[Tornada]"""},
]

# Lletres contrastades amb Viquitexts i la Viquipèdia (Els segadors: text oficial; La Balanguera: l'estrofa
# 1a, 2a i última, com es canten). Acords contrastats amb reculls d'acords i partitures antigues; La
# Santa Espina només té una font d'acords (pendent de revisar tocant-la).
POPULARS = [
    {"titol": "Els segadors", "autor": "Popular · lletra d'Emili Guanyavents", "cos": """\
Em        B7   Em
Catalunya triomfant
Em   G               D  Em
tornarà a ser rica i plena!
Em  G             B7
Endarrera aquesta gent
            Am    B7 Em
tan ufana i tan superba!

[Tornada]
Em
Bon cop de falç!
G          Am
Bon cop de falç,
          B7    D Em
defensors de la terra!
Am         Em
Bon cop de falç!

Em           B7  Em
Ara és hora, segadors!
Em     G             D  Em
Ara és hora d'estar alerta!
Em       G               B7
Per quan vingui un altre juny
            Am     B7 Em
esmolem ben bé les eines!

[Tornada]

Em          B7   Em
Que tremoli l'enemic
Em    G               D Em
en veient la nostra ensenya:
Em      G              B7
com fem caure espigues d'or,
             Am     B7 Em
quan convé seguem cadenes!

[Tornada]"""},
    {"titol": "La Balanguera", "autor": "Joan Alcover · Amadeu Vives", "cos": """\
        F     Gm   Bb
La Balanguera misteriosa,
         F     Bb       C
com una aranya d'art subtil,
          Bb         F
buida que buida sa filosa,
          F            C
de nostra vida treu el fil.
        F     Gm   Bb
Com una parca bé cavil·la
           F    Bb    C
teixint la tela per demà.
        Bb          F
La Balanguera fila, fila,
        Bb    C   F
la Balanguera filarà.

        Gm       Bb    C
Com una parca bé cavil·la
           Gm   Bb    C
teixint la tela per demà.
        Bb          F
La Balanguera fila, fila,
        Bb    C   F
la Balanguera filarà.

Girant l'ullada cap enrere
guaita les ombres de l'avior,
i de la nova primavera
sap on s'amaga la llavor.
Sap que la soca més s'enfila
com més endins pot arrelar.
La Balanguera fila, fila,
la Balanguera filarà.

Sap que la soca més s'enfila
com més endins pot arrelar.
La Balanguera fila, fila,
la Balanguera filarà.

De tradicions i d'esperances
tix la senyera pel jovent,
com qui fa un vel de noviances
amb cabelleres d'or i argent.
De la infantesa qui s'enfila,
de la vellura qui se'n va.
La Balanguera fila, fila,
la Balanguera filarà.

De la infantesa qui s'enfila,
de la vellura qui se'n va.
La Balanguera fila, fila,
la Balanguera filarà."""},
    {"titol": "La Santa Espina", "autor": "Àngel Guimerà · Enric Morera", "cos": """\
A
Som i serem gent catalana
tant si es vol com si no es vol,
D                       C#7
que no hi ha terra més ufana
E                A
sota la capa del sol.

Am                       Dm
Déu va passar-hi en primavera,
         E           Am
i tot cantava al seu pas.
Am                      Dm
Canta la terra encara entera,
     E           Am
i canta que cantaràs.

Am                            C
Canta l'ocell, el riu, la planta,
                     E7
canten la lluna i el sol.
Am                     Dm
Tot treballant la dona canta
           E7         Am
i canta al peu del bressol.

A                      D
I canta a dintre de la terra
     E            A
lo passat jamai passat,
A                           D
i jorns i nits, de serra en serra,
         E              A
com tot, canta el Montserrat.

A
Som i serem gent catalana
tant si es vol com si no es vol,
D                       C#7
que no hi ha terra més ufana
E                A
sota la capa del sol."""},
    {"titol": "El rossinyol", "autor": "Popular catalana", "cos": """\
G
Rossinyol, que vas a França,
rossinyol,
Em
encomana'm a la mare,
     D
rossinyol,
D
d'un bell bocatge,
     C          G
rossinyol, d'un vol.

G
Encomana'm a la mare,
rossinyol,
Em
i a mon pare no pas gaire,
     D
rossinyol,
D
d'un bell bocatge,
     C          G
rossinyol, d'un vol.

G
I a mon pare no pas gaire,
rossinyol,
Em
perquè m'ha mal maridada,
     D
rossinyol,
D
d'un bell bocatge,
     C          G
rossinyol, d'un vol.

G
Perquè m'ha mal maridada,
rossinyol,
Em
a un pastor me n'ha dada,
     D
rossinyol,
D
d'un bell bocatge,
     C          G
rossinyol, d'un vol.

G
A un pastor me n'ha dada,
rossinyol,
Em
que em fa guardar la ramada,
     D
rossinyol,
D
d'un bell bocatge,
     C          G
rossinyol, d'un vol.

G
Que em fa guardar la ramada,
rossinyol,
Em
he perduda l'esquellada,
     D
rossinyol,
D
d'un bell bocatge,
     C          G
rossinyol, d'un vol."""},
    {"titol": "El gegant del Pi", "autor": "Popular catalana", "cos": """\
     G
El gegant del Pi
    D          G
ara balla, ara balla,
el gegant del Pi
    D           G
ara balla pel camí.

     G
El gegant de la Ciutat
    D          G
ara balla, ara balla,
el gegant de la Ciutat
    D           G
ara balla pel terrat.

     G
La tintina del gegant
    D          G
ara passa, ara passa,
la tintina del gegant
    D           G
ara passa pel davant."""},
    {"titol": "Plou i fa sol", "autor": "Popular catalana", "cos": """\
C
Plou i fa sol,
    G             C
les bruixes es pentinen,
C
plou i fa sol,
    G              C
les bruixes porten dol.

C
Plou i fa sol,
    G             C
les bruixes es pentinen,
C
plou i fa sol,
    G            C
les bruixes fan un ou."""},
    {"titol": "Cargol treu banya", "autor": "Popular catalana", "cos": """\
   G
Cargol, treu banya,
puja a la muntanya;
   D         G
cargol, treu vi,
D            G
puja al muntanyí.

   G
Cargol, treu banya,
puja a la muntanya;
   D     G
cargol bover,
D           G
jo també vindré."""},
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
                                          contraportada="Cançons de domini públic.\nBona cantada!",
                                          especials={"portada": plantilles.portada_completa()})
    for c in base["cancons"]:
        id_canco = basedades.crea_canco(c["titol"], c["autor"], document.de_text(c["cos"]))
        basedades.crea_versio(id_canco, "Versió inicial")
        basedades.afegeix_entrada(id_canconer, id_canco)
    return id_canconer
