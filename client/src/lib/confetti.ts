function random(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

export function fireConfettiBurst(): void {
  const colors = ["#22c55e", "#f59e0b", "#3b82f6", "#ef4444", "#8b5cf6"];
  const total = 36;
  for (let i = 0; i < total; i += 1) {
    const piece = document.createElement("span");
    piece.style.position = "fixed";
    piece.style.left = `${random(20, 80)}vw`;
    piece.style.top = "14vh";
    piece.style.width = "8px";
    piece.style.height = "12px";
    piece.style.zIndex = "9999";
    piece.style.pointerEvents = "none";
    piece.style.borderRadius = "2px";
    piece.style.background = colors[i % colors.length];
    piece.style.transform = `translate3d(0,0,0) rotate(${random(0, 360)}deg)`;
    piece.style.transition = `transform 2500ms cubic-bezier(.2,.8,.2,1), opacity 2500ms ease`;
    document.body.appendChild(piece);

    requestAnimationFrame(() => {
      piece.style.opacity = "0";
      piece.style.transform = `translate3d(${random(-140, 140)}px, ${random(220, 420)}px, 0) rotate(${random(360, 720)}deg)`;
    });

    window.setTimeout(() => {
      piece.remove();
    }, 2700);
  }
}
