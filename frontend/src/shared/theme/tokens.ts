// デザイン値のハードコード禁止。色・タイポ・形状はここを経由する。
// 値の真実源は docs/requirements/03-spec.md「3. デザイントークン」（A案「検印」）。ここは転記。
export const tokens = {
  colors: {
    // 色相は main と error の2つだけ。他はすべて濃淡
    main: {
      100: "#EEF1F7", // 淡い背景・ホバー・表の見出し行・除外した行
      300: "#B9C3D9", // 枠線・罫線・補助
      500: "#4A5E8C", // 通常ボタンの枠・「要確認」の点線枠
      700: "#2E3F66", // 主要アクション・リンク・検印・強調
      900: "#1B2641", // 濃い強調・製品名
    },
    background: "#F6F7FA",
    surface: "#FBFCFD",
    text: {
      primary: "#1F2330",
      secondary: "#4B5163",
      meta: "#62697D",
    },
    error: "#B3261E",
  },
  typography: {
    fontHeading: '"Hiragino Mincho ProN", "Yu Mincho", "Noto Serif JP", serif',
    fontBody:
      '"Hiragino Sans", "Yu Gothic", "Noto Sans JP", system-ui, sans-serif',
    size: { xl: 22, lg: 18, md: 15, sm: 13, xs: 11 },
    weight: { body: 400, label: 600, heading: 700 },
  },
  radius: 2,
  spacing: (n: number) => n * 8,
} as const;
