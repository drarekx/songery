// Ordre de les capes al panell de capes.

/** Els membres d'un grup van junts, sota una capçalera, a l'altura del primer (el de més davant). */
export function ordenaCapes(elements) {
  const ordre = [];
  const vistos = new Set();
  for (const e of elements) {
    if (!e.grup) ordre.push(e);
    else if (!vistos.has(e.grup)) {
      vistos.add(e.grup);
      const membres = elements.filter((x) => x.grup === e.grup);
      ordre.push({ capcalera: e.grup, membres }, ...membres);
    }
  }
  return ordre;
}
