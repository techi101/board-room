// Home page motion: rotating interview type in the headline, and the speaking tile + caption cycling in the call mock.
(() => {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const words = ["UPSC board", "placement panel", "MBA interview", "CA interview", "bank PO board", "PSU interview", "consulting case"];
  const rot = document.getElementById("rot");
  let w = 0;
  if (rot) setInterval(() => {
    rot.classList.add("out");
    setTimeout(() => { w = (w + 1) % words.length; rot.textContent = words[w]; rot.classList.remove("out"); }, 320);
  }, 2600);

  const lines = [
    [0, "Tech Lead", "I opened your repo. In your api folder, index.js points the database to the tmp folder. On Vercel, what happens to that file when the function goes cold?"],
    [2, "Senior Engineer", "Your rollout is a percentage. How do you make sure the same user always gets the same answer?"],
    [1, "HR Partner", "Tell me briefly about something you built recently that you are proud of."],
  ];
  const tiles = document.querySelectorAll(".call .tile[data-tile]");
  const who = document.querySelector(".call .caption b"), cap = document.getElementById("capText");
  let i = 0, typer;
  const say = ([t, name, text]) => {
    tiles.forEach((el) => el.classList.toggle("on", +el.dataset.tile === t));
    if (!who || !cap) return;
    who.textContent = name; cap.textContent = "";
    let k = 0; clearInterval(typer);
    typer = setInterval(() => { cap.textContent = text.slice(0, ++k); if (k >= text.length) clearInterval(typer); }, 28);
  };
  if (tiles.length) setInterval(() => { i = (i + 1) % lines.length; say(lines[i]); }, 7000);
})();
