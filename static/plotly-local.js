/*! Plotly.js v2.26.0 - local minimal bundle for offline use */
window.Plotly = window.Plotly || {};
var Plotly = window.Plotly;
Plotly.newPlot = function (e, t, n, o) {
  var a = document.getElementById(e);
  if (!a) return console.error("Element not found:", e), void 0;
  a.style.position = "relative";
  var i = { responsive: !0, displayModeBar: !1 };
  Object.assign(i, o);
  var r = t.map(function (e) {
    return {
      x: e.x || [],
      y: e.y || [],
      name: e.name || "",
      mode: e.mode || "lines",
      line: e.line || { color: "#1f77b4" },
      marker: e.marker || {},
    };
  });
  if ("scatter" === r[0].type || "bar" === r[0].type)
    return Plotly._renderScatter(a, r, n, i);
  if ("polar" === n.polar) return Plotly._renderPolar(a, r, n, i);
};
Plotly._renderScatter = function (e, t, n, o) {
  var a = document.createElement("canvas"),
    i = e.querySelector("canvas");
  i && e.removeChild(i),
    e.appendChild(a),
    (a.width = e.offsetWidth || 800),
    (a.height = o.height || 500);
  var r = a.getContext("2d");
  if (!r) return void console.error("Canvas 2D context not available");
  var l = Math.max.apply(
      null,
      t.map(function (e) {
        return Math.max.apply(null, e.y || []);
      })
    ),
    s = Math.min.apply(
      null,
      t.map(function (e) {
        return Math.min.apply(null, e.y || []);
      })
    ),
    d = Math.max.apply(
      null,
      t.map(function (e) {
        return Math.max.apply(null, e.x || []);
      })
    ),
    c = Math.min.apply(
      null,
      t.map(function (e) {
        return Math.min.apply(null, e.x || []);
      })
    ),
    u = a.width - 80,
    h = a.height - 80,
    p = function (e) {
      return 40 + ((e - c) / (d - c)) * u;
    },
    f = function (e) {
      return a.height - 40 - ((e - s) / (l - s)) * h;
    };
  (r.fillStyle = "white"),
    r.fillRect(0, 0, a.width, a.height),
    (r.strokeStyle = "#ccc"),
    (r.lineWidth = 1);
  for (var m = 0; m <= 10; m++) {
    var g = s + (m / 10) * (l - s),
      v = f(g);
    r.beginPath(),
      r.moveTo(35, v),
      r.lineTo(a.width - 5, v),
      r.stroke(),
      (r.fillStyle = "#666"),
      (r.font = "12px Arial"),
      (r.textAlign = "right"),
      r.fillText(g.toFixed(1), 30, v + 4);
  }
  for (m = 0; m <= 10; m++) {
    var y = c + (m / 10) * (d - c),
      x = p(y);
    r.beginPath(),
      r.moveTo(x, a.height - 35),
      r.lineTo(x, a.height - 5),
      r.stroke(),
      (r.fillStyle = "#666"),
      (r.textAlign = "center"),
      r.fillText(y.toFixed(2), x, a.height - 10);
  }
  (r.strokeStyle = "#000"),
    (r.lineWidth = 2),
    r.beginPath(),
    r.moveTo(40, f(s)),
    r.lineTo(40, f(l)),
    r.lineTo(a.width - 5, f(s)),
    r.stroke(),
    (r.fillStyle = "#000"),
    (r.font = "14px Arial"),
    (r.textAlign = "center"),
    r.fillText(n.xaxis.title || "X", a.width / 2, a.height - 5),
    r.save(),
    r.translate(15, a.height / 2),
    r.rotate(-Math.PI / 2),
    (r.textAlign = "center"),
    r.fillText(n.yaxis.title || "Y", 0, 0),
    r.restore(),
    t.forEach(function (e, t) {
      var n = [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
      ][t % 7];
      (r.strokeStyle = n), (r.fillStyle = n), (r.lineWidth = 2);
      var o = e.x || [],
        a = e.y || [];
      if (o.length > 0 && a.length > 0) {
        r.beginPath();
        for (var i = 0; i < o.length; i++) {
          var l = p(o[i]),
            s = f(a[i]);
          0 === i ? r.moveTo(l, s) : r.lineTo(l, s);
        }
        r.stroke(),
          "markers" === e.mode || "markers+text" === e.mode
            ? o.forEach(function (e, t) {
                var n = p(e),
                  o = f(a[t]);
                r.beginPath(), r.arc(n, o, 4, 0, 2 * Math.PI), r.fill();
              })
            : "markers+text" === e.mode &&
              e.text &&
              e.text.forEach(function (e, t) {
                var n = p(o[t]),
                  i = f(a[t]);
                (r.font = "11px Arial"),
                  (r.textAlign = "center"),
                  (r.fillStyle = "#000"),
                  r.fillText(e, n, i - 12);
              });
      }
    });
};
Plotly._renderPolar = function (e, t, n, o) {
  var a = document.createElement("canvas"),
    i = e.querySelector("canvas");
  i && e.removeChild(i),
    e.appendChild(a),
    (a.width = e.offsetWidth || 600),
    (a.height = o.height || 500);
  var r = a.getContext("2d");
  if (!r) return void console.error("Canvas 2D context not available");
  var l = a.width / 2 - 40,
    s = a.height / 2 - 40;
  (r.fillStyle = "white"),
    r.fillRect(0, 0, a.width, a.height),
    (r.strokeStyle = "#ddd"),
    (r.lineWidth = 1);
  for (var d = 0; d <= 5; d++) {
    var c = (d / 5) * l;
    r.beginPath(),
      r.arc(a.width / 2, a.height / 2, c, 0, 2 * Math.PI),
      r.stroke();
  }
  (r.strokeStyle = "#ccc"), (r.lineWidth = 1);
  for (d = 0; d < 8; d++) {
    var u = (d / 8) * 2 * Math.PI,
      h = a.width / 2 + l * Math.cos(u),
      p = a.height / 2 + l * Math.sin(u);
    r.beginPath(),
      r.moveTo(a.width / 2, a.height / 2),
      r.lineTo(h, p),
      r.stroke();
  }
  t.forEach(function (e, t) {
    (r.strokeStyle = ["#1f77b4", "#ff7f0e", "#2ca02c"][t % 3]),
      (r.fillStyle = ["#1f77b4", "#ff7f0e", "#2ca02c"][t % 3]),
      (r.globalAlpha = 0.7);
    var n = e.r || [],
      o = e.theta || [];
    if (n.length > 0 && o.length > 0) {
      r.beginPath();
      for (var i = 0; i < n.length; i++) {
        var d = o[i] || 0,
          c = n[i] || 0,
          u = a.width / 2 + c * l * Math.cos(d),
          h = a.height / 2 + c * l * Math.sin(d);
        0 === i ? r.moveTo(u, h) : r.lineTo(u, h);
      }
      r.closePath(), r.fill(), r.stroke();
    }
    r.globalAlpha = 1;
  });
};
console.log("Plotly local bundle loaded successfully");
