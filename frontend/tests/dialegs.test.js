// Diàlegs de l'aplicació: confirmar, avisar i preguntar (en lloc dels del navegador).
import { afterEach, describe, expect, it } from "vitest";
import { avisa, confirma, pregunta } from "@/dialegs.js";

afterEach(() => { document.body.innerHTML = ""; });
const dialeg = () => document.querySelector("dialog.dialeg-app:not(.tancant)"); // el que s'està tancant (animació) no
const clica = (text) => [...dialeg().querySelectorAll("button")].find((b) => b.textContent === text).click();

describe("diàlegs", () => {
  it("confirmar: sí o no", async () => {
    const resposta = confirma({ titol: "Esborrar la pàgina?", text: "Ho pots desfer.", accepta: "Esborra", perill: true });
    expect(dialeg().textContent).toContain("Esborrar la pàgina?");
    expect(dialeg().classList).toContain("dialeg-perill");
    expect(document.activeElement.textContent).toBe("Cancel·la"); // en un perill, el focus no és a «Esborra»
    clica("Esborra");
    expect(await resposta).toBe(true);
    const no = confirma({ titol: "Segur?" });
    clica("Cancel·la");
    expect(await no).toBe(false);
  });

  it("avisar: només un botó", async () => {
    const fet = avisa({ titol: "No n'hi caben més", text: "Com a màxim 20." });
    expect(dialeg().querySelectorAll("button")).toHaveLength(1);
    clica("D'acord");
    expect(await fet).toBe(true);
  });

  it("preguntar: torna el text, o null si es cancel·la; buit no es pot desar", async () => {
    const nom = pregunta({ titol: "Pàgina mestra nova", valor: "Mestra nova" });
    const camp = dialeg().querySelector("input");
    expect(camp.value).toBe("Mestra nova");
    camp.value = "  ";
    camp.dispatchEvent(new Event("input"));
    expect([...dialeg().querySelectorAll("button")].find((b) => b.textContent === "Desa").disabled).toBe(true);
    camp.value = " Banda vermella ";
    camp.dispatchEvent(new Event("input"));
    clica("Desa");
    expect(await nom).toBe("Banda vermella");
    const cap = pregunta({ titol: "Nom" });
    clica("Cancel·la");
    expect(await cap).toBeNull();
  });

  it("els formularis amb data-confirma demanen confirmació abans d'enviar-se", async () => {
    document.body.innerHTML = '<form data-confirma="No es pot desfer." data-confirma-titol="Buidar?"><button>Buida</button></form>';
    const form = document.querySelector("form");
    let enviat = false;
    form.submit = () => { enviat = true; };
    form.requestSubmit(form.querySelector("button"));
    await Promise.resolve();
    expect(dialeg().textContent).toContain("Buidar?");
    expect(enviat).toBe(false);
    clica("Buida");
    await new Promise((r) => setTimeout(r, 0));
    expect(enviat).toBe(true);
  });
});
