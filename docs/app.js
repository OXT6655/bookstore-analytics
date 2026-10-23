(function () {
  const desk = window.DESK;
  const panel = document.getElementById("panel");
  const storeSwitch = document.getElementById("store-switch");
  if (!desk || !desk.stores) {
    panel.textContent = "Dashboard data was not generated. Run python -m bookstore_analytics.";
    return;
  }

  const state = { storeIndex: 0, tab: "revenue", chats: {} };
  const STOP = new Set(
    "how many what who whom whose why when where which show list find search tell give the a an of to for and or in on with by from about unique users user customer customers real number count sets set author authors book books sold copies popular most top buyer best spending spend alias aliases changed change phone phones name names address email emails id ids store revenue day days please me my is are was were there their this that these those into over under did does do sold sale sales write wrote together collaboration collaborations solo explain define meaning mean same person people record records".split(" ")
  );

  function store() {
    return desk.stores[state.storeIndex];
  }

  function esc(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function money(cents) {
    const abs = Math.abs(cents);
    const dollars = Math.floor(abs / 100).toLocaleString("en-US");
    const rem = String(abs % 100).padStart(2, "0");
    return (cents < 0 ? "-$" : "$") + dollars + "." + rem;
  }

  function idList(ids) {
    return "[" + ids.join(", ") + "]";
  }

  function joinAuthors(names) {
    if (names.length <= 1) return names[0] || "Unknown";
    if (names.length === 2) return names[0] + " and " + names[1];
    return names.slice(0, -1).join(", ") + ", and " + names[names.length - 1];
  }

  function chatKey() {
    return state.storeIndex + ":" + state.tab;
  }

  function messages() {
    const key = chatKey();
    if (!state.chats[key]) {
      state.chats[key] = [{ role: "bot", text: welcome(store(), state.tab) }];
    }
    return state.chats[key];
  }

  function welcome(current, tab) {
    if (tab === "customers") {
      return (
        "Ask about real customers in " + current.store + ".\n" +
        current.unique_users.toLocaleString("en-US") +
        " people sit behind " + current.audit.users_used.toLocaleString("en-US") +
        " user records. I can explain a merge, look up an id or a name, and name the best buyer."
      );
    }
    const popular = current.most_popular[0];
    return (
      "Ask about author sets in " + current.store + ".\n" +
      "There are " + current.unique_author_sets.toLocaleString("en-US") +
      " distinct sets. The most sold is " + joinAuthors(popular.authors) +
      " with " + popular.copies.toLocaleString("en-US") + " copies."
    );
  }

  function sizeSentence(sizes) {
    const labels = { 1: "once", 2: "as a pair", 3: "as a trio" };
    return Object.keys(sizes)
      .map(function (size) {
        const count = sizes[size];
        const phrase = labels[size] || "in groups of " + size;
        return count.toLocaleString("en-US") + " " + phrase;
      })
      .join(", ");
  }

  function bestBuyerText(current) {
    if (!current.best_buyers.length) return "No paid orders are tied to a known customer.";
    return current.best_buyers
      .map(function (buyer) {
        const changed = buyer.changed.length ? buyer.changed.join(", ") : "no field";
        return (
          "Best buyer spend is " + money(buyer.spend_cents) +
          " across " + buyer.copies.toLocaleString("en-US") + " copies.\n" +
          "Ids: " + idList(buyer.ids) + "\n" +
          "Names: " + (buyer.names.join("; ") || "—") + "\n" +
          "Phones: " + (buyer.phones.join("; ") || "—") + "\n" +
          "Emails: " + (buyer.emails.join("; ") || "—") + "\n" +
          "Addresses: " + (buyer.addresses.join("; ") || "—") + "\n" +
          "Fields that differ inside the group: " + changed + "."
        );
      })
      .join("\n\n");
  }

  function lookupCluster(cluster) {
    if (!cluster) return "That id is not in this store.";
    const changed = cluster.changed.length ? cluster.changed.join(", ") : "nothing — this is a single record";
    return (
      "Ids: " + idList(cluster.ids) + "\n" +
      "Names: " + (cluster.names.join("; ") || "—") + "\n" +
      "Phones: " + (cluster.phones.join("; ") || "—") + "\n" +
      "Emails: " + (cluster.emails.join("; ") || "—") + "\n" +
      "Addresses: " + (cluster.addresses.join("; ") || "—") + "\n" +
      "Spend: " + money(cluster.spend_cents) + "\n" +
      "What differs: " + changed + "."
    );
  }

  function tokensOf(question) {
    return question
      .toLowerCase()
      .replace(/[^a-z0-9@.\s'-]/g, " ")
      .split(/\s+/)
      .filter(function (token) { return token.length > 2 && !STOP.has(token); });
  }

  function matchesTokens(text, tokens) {
    const hay = text.toLowerCase();
    return tokens.some(function (token) { return hay.includes(token); });
  }

  function answerCustomers(current, question) {
    const lower = question.toLowerCase();
    const idMatch = lower.match(/\b(\d{4,})\b/);
    if (/best buyer|top customer|highest spend|most spent|biggest customer|who spent/.test(lower)) {
      return bestBuyerText(current);
    }
    if (idMatch) {
      const id = Number(idMatch[1]);
      const cluster = current.clusters.find(function (item) { return item.ids.indexOf(id) !== -1; });
      return lookupCluster(cluster);
    }
    if (/how many|unique|number of|count/.test(lower)) {
      return (
        current.unique_users.toLocaleString("en-US") + " real customers.\n" +
        current.audit.users_used.toLocaleString("en-US") + " raw rows. " +
        current.audit.multi_record_people.toLocaleString("en-US") +
        " people have more than one row (" +
        current.audit.records_in_merged_people.toLocaleString("en-US") + " rows).\n" +
        "Group sizes: " + sizeSentence(current.audit.component_sizes) + "."
      );
    }
    if (/how|why|method|reconcil|match|assume|one field|alias|rule/.test(lower)) {
      return (
        "Two rows are the same person when at most one of name, address, phone, and email differs. " +
        "Phones are compared on their last 10 digits. Text ignores case and repeated spaces. " +
        "A blank address is not treated as a shared address.\n" +
        "If A matches B and B matches C, all three stay one person: each step changes a single field, even when the ends differ in two.\n" +
        "This store: " + current.unique_users.toLocaleString("en-US") + " people from " +
        current.audit.users_used.toLocaleString("en-US") + " rows."
      );
    }
    const field = /phone/.test(lower) ? "phone"
      : /e-?mail/.test(lower) ? "email"
      : /address/.test(lower) ? "address"
      : /\bname|alias/.test(lower) ? "name"
      : "";
    if (field && /chang|differ|alias|instead|merge|example|show/.test(lower)) {
      const rows = current.clusters.filter(function (item) { return item.changed.indexOf(field) !== -1; });
      if (!rows.length) return "No customer group in this store differs by " + field + ".";
      const sample = rows.slice(0, 4).map(function (item) {
        const values = item[field + "s"] || item[field] || [];
        const shown = (item[field === "address" ? "addresses" : field + "s"] || []).join("  |  ");
        return idList(item.ids) + " — " + item.names.join(" / ") + " — " + shown;
      }).join("\n");
      return rows.length.toLocaleString("en-US") + " customer groups differ by " + field + ". Highest spenders:\n" + sample;
    }
    const tokens = tokensOf(question);
    if (tokens.length) {
      const found = current.clusters.filter(function (item) {
        return item.names.some(function (name) { return matchesTokens(name, tokens); })
          || item.emails.some(function (email) { return matchesTokens(email, tokens); });
      });
      if (found.length) {
        const lines = found.slice(0, 5).map(lookupCluster).join("\n\n");
        const extra = found.length > 5 ? "\n\nShowing 5 of " + found.length + "." : "";
        return lines + extra;
      }
    }
    return "I can answer how many real customers there are, why rows were merged, which groups changed a phone, name, address, or email, who the best buyer is, and lookups by id or name.";
  }

  function answerAuthors(current, question) {
    const lower = question.toLowerCase();
    if (/how many|unique|number of|count/.test(lower)) {
      return (
        current.unique_author_sets.toLocaleString("en-US") + " unique author sets in the catalogue.\n" +
        current.audit.solo_author_sets.toLocaleString("en-US") + " are a single name. " +
        current.audit.collaborative_author_sets.toLocaleString("en-US") +
        " are collaborations. John with Paul is a different set from John alone, even if both names also appear on other books."
      );
    }
    if (/popular|most sold|sold the most|best.?sell|top author|who sold|copies/.test(lower) && !/top\s*[0-9]|ranking|list/.test(lower)) {
      if (!current.most_popular.length) return "No copies are tied to a known author set.";
      return current.most_popular.map(function (item) {
        const titles = item.titles.slice(0, 8).map(function (title) { return "• " + title; }).join("\n");
        const more = item.title_count > item.titles.length ? "\n… " + (item.title_count - item.titles.length) + " more titles" : "";
        return joinAuthors(item.authors) + " — " + item.copies.toLocaleString("en-US") +
          " copies across " + item.title_count + " titles.\n" + titles + more;
      }).join("\n\n");
    }
    if (/solo|alone|collaboration|together|joint/.test(lower)) {
      return current.audit.solo_author_sets.toLocaleString("en-US") + " sets are one author. " +
        current.audit.collaborative_author_sets.toLocaleString("en-US") + " sets have two or more names.";
    }
    if (/what is a set|author set|define|mean/.test(lower)) {
      return "An author set is the exact group of names on a book, split on commas. Order and capitalisation do not create a new set. Several books by the same group still count once. Popularity is the sum of copies sold, not the number of titles.";
    }
    if (/top|rank|list/.test(lower)) {
      const lines = current.author_sets.slice(0, 8).map(function (item, index) {
        return (index + 1) + ". " + joinAuthors(item.authors) + " — " + item.copies.toLocaleString("en-US") + " copies";
      }).join("\n");
      return "Highest sets by copies sold:\n" + lines;
    }
    const tokens = tokensOf(question);
    if (tokens.length) {
      const found = current.author_sets.filter(function (item) {
        return item.authors.some(function (name) { return matchesTokens(name, tokens); });
      });
      if (found.length) {
        const lines = found.slice(0, 6).map(function (item) {
          const titles = item.titles.slice(0, 4).join("; ");
          return joinAuthors(item.authors) + " — " + item.copies.toLocaleString("en-US") + " copies. " + titles;
        }).join("\n");
        const extra = found.length > 6 ? "\nShowing 6 of " + found.length + "." : "";
        return lines + extra;
      }
    }
    return "I can answer how many author sets there are, which set sold the most copies, how many are collaborations, and which books a name appears on.";
  }

  function chartMarkup(series) {
    const width = 920;
    const height = 320;
    const pad = { l: 64, r: 16, t: 16, b: 36 };
    const maxCents = Math.max.apply(null, series.map(function (item) { return item.cents; }).concat([1]));
    const step = maxCents / 100 > 3000 ? 1000 : 500;
    const maxDollars = Math.max(step, Math.ceil(maxCents / 100 / step) * step);
    const max = maxDollars * 100;
    const innerW = width - pad.l - pad.r;
    const innerH = height - pad.t - pad.b;
    const n = series.length;
    function x(index) { return pad.l + (n === 1 ? innerW / 2 : (index / (n - 1)) * innerW); }
    function y(cents) { return pad.t + innerH - (cents / max) * innerH; }
    const points = series.map(function (item, index) {
      return x(index).toFixed(1) + "," + y(item.cents).toFixed(1);
    }).join(" ");
    const base = (pad.t + innerH).toFixed(1);
    const area = pad.l + "," + base + " " + points + " " + (pad.l + innerW).toFixed(1) + "," + base;
    let grid = "";
    for (let dollars = 0; dollars <= maxDollars; dollars += step) {
      const yy = y(dollars * 100).toFixed(1);
      grid += '<line class="gridline" x1="' + pad.l + '" y1="' + yy + '" x2="' + (width - pad.r) + '" y2="' + yy + '"></line>';
      grid += '<text x="' + (pad.l - 8) + '" y="' + (Number(yy) + 4) + '" text-anchor="end">$' + dollars.toLocaleString("en-US") + "</text>";
    }
    const months = [];
    series.forEach(function (item, index) {
      const month = item.date.slice(0, 7);
      if (!months.length || months[months.length - 1].month !== month) months.push({ month: month, index: index });
    });
    const labels = months.filter(function (_item, index) {
      return index % 2 === 0 || index === months.length - 1;
    }).map(function (item) {
      return '<text x="' + x(item.index).toFixed(1) + '" y="' + (height - 10) + '" text-anchor="middle">' + item.month + "</text>";
    }).join("");
    return (
      '<svg id="revenue-chart" viewBox="0 0 ' + width + " " + height + '" role="img" aria-label="Daily revenue">' +
      grid +
      '<polygon points="' + area + '" fill="#1d4e89" opacity="0.12"></polygon>' +
      '<polyline points="' + points + '" fill="none" stroke="#1d4e89" stroke-width="2"></polyline>' +
      '<line id="chart-cursor" x1="0" y1="' + pad.t + '" x2="0" y2="' + (pad.t + innerH) + '" stroke="#9a4324" stroke-width="1" visibility="hidden"></line>' +
      labels +
      "</svg>"
    );
  }

  function bindChart(series) {
    const svg = document.getElementById("revenue-chart");
    const tip = document.getElementById("chart-tip");
    if (!svg || !tip || !series.length) return;
    const pad = { l: 64, r: 16 };
    const width = 920;
    const innerW = width - pad.l - pad.r;
    function place(event) {
      const rect = svg.getBoundingClientRect();
      const vx = ((event.clientX - rect.left) / rect.width) * width;
      let index = Math.round(((vx - pad.l) / innerW) * (series.length - 1));
      index = Math.max(0, Math.min(series.length - 1, index));
      const point = series[index];
      const cursor = document.getElementById("chart-cursor");
      const x = pad.l + (index / (series.length - 1)) * innerW;
      cursor.setAttribute("x1", x);
      cursor.setAttribute("x2", x);
      cursor.setAttribute("visibility", "visible");
      tip.hidden = false;
      tip.textContent = point.date + "  ·  " + money(point.cents);
      const wrap = svg.parentElement.getBoundingClientRect();
      tip.style.left = Math.min(event.clientX - wrap.left + 12, wrap.width - 160) + "px";
      tip.style.top = Math.max(event.clientY - wrap.top - 36, 8) + "px";
    }
    svg.addEventListener("mousemove", place);
    svg.addEventListener("mouseleave", function () {
      tip.hidden = true;
      document.getElementById("chart-cursor").setAttribute("visibility", "hidden");
    });
  }

  function renderRevenue(current) {
    const daysWithSales = current.daily_revenue.filter(function (item) { return item.cents > 0; }).length;
    const topRows = current.top5_days.map(function (item, index) {
      const share = current.total_cents ? (100 * item.cents / current.total_cents) : 0;
      return "<tr><td>" + (index + 1) + '</td><td class="date">' + item.date +
        '</td><td class="num">' + money(item.cents) + '</td><td class="num">' + share.toFixed(2) + "%</td></tr>";
    }).join("");
    const tie = current.top5_tie_dates.length
      ? '<p class="note">The same revenue also falls on ' + current.top5_tie_dates.join(", ") + ".</p>"
      : "";
    const first = current.daily_revenue[0];
    const last = current.daily_revenue[current.daily_revenue.length - 1];
    return (
      '<section class="answer"><p class="kicker">Top 5 days by revenue</p><h2>' +
      current.top5_days.map(function (item) { return item.date; }).join(" · ") +
      "</h2><p>Dates are YYYY-MM-DD. Ranked by paid price, then by date.</p></section>" +
      '<div class="grid kpis">' +
      kpi("Total revenue", money(current.total_cents), true) +
      kpi("Orders", current.order_count.toLocaleString("en-US"), false) +
      kpi("Peak day", current.top5_days[0].date, false) +
      kpi("Euro lines converted", current.audit.eur_lines.toLocaleString("en-US"), false) +
      "</div>" +
      '<div class="grid split">' +
      '<article class="card"><h3>Top 5 days</h3><table><thead><tr><th>#</th><th>Date</th><th class="num">Revenue</th><th class="num">Share</th></tr></thead><tbody>' +
      topRows + "</tbody></table>" + tie + "</article>" +
      '<article class="card"><h3>Daily revenue</h3><div class="chart-wrap"><div id="chart-tip" class="tip" hidden></div>' +
      chartMarkup(current.daily_revenue) + "</div>" +
      '<p class="note">' + first.date + " to " + last.date + " · " +
      current.daily_revenue.length.toLocaleString("en-US") + " calendar days · " +
      daysWithSales.toLocaleString("en-US") + " with sales. Empty days are drawn as zero.</p></article></div>" +
      '<p class="note">Paid price is quantity times the unit price in dollars. A mark between the major units and the cents, as in 70€99¢ or $20¢25, is the decimal point. ' +
      current.audit.books_bad_year + " catalogue years were blank or not a year and were left empty; those books still count.</p>"
    );
  }

  function kpi(label, value, accent) {
    return '<article class="card kpi' + (accent ? " accent" : "") + '"><div class="value">' + esc(value) +
      '</div><div class="label">' + esc(label) + "</div></article>";
  }

  function buyerCard(buyer, tied) {
    const names = buyer.names.length ? buyer.names.map(esc).join("<br>") : "—";
    return (
      '<article class="card"><p class="kicker">' + (tied ? "Tied best buyer" : "Best buyer") + "</p>" +
      '<p class="names">' + money(buyer.spend_cents) + "</p>" +
      '<div class="id-row"><code>' + esc(idList(buyer.ids)) + "</code>" +
      '<button type="button" class="copy" data-copy="' + esc(idList(buyer.ids)) + '">Copy ids</button></div>' +
      '<dl class="facts"><dt>Names</dt><dd>' + names + "</dd>" +
      "<dt>Phones</dt><dd>" + (buyer.phones.map(esc).join("<br>") || "—") + "</dd>" +
      "<dt>Emails</dt><dd>" + (buyer.emails.map(esc).join("<br>") || "—") + "</dd>" +
      "<dt>Addresses</dt><dd>" + (buyer.addresses.map(esc).join("<br>") || "—") + "</dd>" +
      "<dt>Copies</dt><dd>" + buyer.copies.toLocaleString("en-US") + "</dd></dl></article>"
    );
  }

  function renderCustomers(current) {
    const buyers = current.best_buyers.map(function (buyer) {
      return buyerCard(buyer, current.best_buyers.length > 1);
    }).join("");
    return (
      '<section class="answer"><p class="kicker">Real customers</p><h2>' +
      current.unique_users.toLocaleString("en-US") + "</h2>" +
      "<p>" + current.audit.users_used.toLocaleString("en-US") + " raw rows, " +
      current.audit.multi_record_people.toLocaleString("en-US") +
      " people with more than one record. " + sizeSentence(current.audit.component_sizes) + ".</p></section>" +
      '<div class="grid split"><div class="stack">' + buyers +
      '<article class="card"><h3>How a person is recognised</h3><p class="note" style="margin-top:0">Rows link when they match on every field except one of name, address, phone, or email. A later row may change a different field; the whole chain is still one customer. The id array lists every user id in that chain.</p></article></div>' +
      chatBox(
        "Customer chat",
        "Merges, aliases, and the best buyer for " + current.store + ".",
        ["How many real customers?", "Who is the best buyer?", "Show a changed phone", "How are aliases matched?"]
      ) + "</div>"
    );
  }

  function renderAuthors(current) {
    const cards = current.most_popular.map(function (item) {
      return (
        '<article class="card"><p class="kicker">Most popular author set</p><p class="names">' +
        esc(joinAuthors(item.authors)) + "</p><p>" + item.copies.toLocaleString("en-US") +
        " copies · " + item.title_count + " titles</p>" +
        (item.authors.length > 1 ? '<p><span class="pill">One set, listed together</span></p>' : '<p><span class="pill">Single author</span></p>') +
        "</article>"
      );
    }).join("");
    const rows = current.author_sets.slice(0, 8).map(function (item, index) {
      return "<tr><td>" + (index + 1) + "</td><td>" + esc(joinAuthors(item.authors)) +
        '</td><td class="num">' + item.copies.toLocaleString("en-US") +
        '</td><td class="num">' + item.titles.length + "</td></tr>";
    }).join("");
    return (
      '<section class="answer"><p class="kicker">Unique author sets</p><h2>' +
      current.unique_author_sets.toLocaleString("en-US") + "</h2>" +
      "<p>" + current.audit.solo_author_sets.toLocaleString("en-US") + " solo sets and " +
      current.audit.collaborative_author_sets.toLocaleString("en-US") +
      " collaborations. Sets come from the catalogue, not only from books that sold.</p></section>" +
      '<div class="grid kpis">' +
      kpi("Sets", current.unique_author_sets.toLocaleString("en-US"), true) +
      kpi("Solo", current.audit.solo_author_sets.toLocaleString("en-US"), false) +
      kpi("Collaborations", current.audit.collaborative_author_sets.toLocaleString("en-US"), false) +
      kpi("Top copies", current.most_popular[0].copies.toLocaleString("en-US"), false) +
      "</div>" +
      '<div class="grid split"><div class="stack">' + cards + "</div>" +
      chatBox(
        "Author-set chat",
        "Sets, collaborations, and the best-selling names in " + current.store + ".",
        ["How many author sets?", "Who sold the most copies?", "How many are collaborations?", "Show the top sets"]
      ) + "</div>" +
      '<article class="card" style="margin-top:14px"><h3>Highest sets by copies</h3><table><thead><tr><th>#</th><th>Author set</th><th class="num">Copies</th><th class="num">Titles</th></tr></thead><tbody>' +
      rows + "</tbody></table></article>"
    );
  }

  function chatBox(title, subtitle, prompts) {
    const history = messages().map(function (message) {
      return '<div class="bubble ' + message.role + '">' + esc(message.text) + "</div>";
    }).join("");
    const chips = prompts.map(function (prompt) {
      return '<button type="button" data-prompt="' + esc(prompt) + '">' + esc(prompt) + "</button>";
    }).join("");
    return (
      '<section class="chat"><header><h3>' + esc(title) + "</h3><p>" + esc(subtitle) + "</p></header>" +
      '<div class="log" id="chat-log">' + history + "</div>" +
      '<div class="chips">' + chips + "</div>" +
      '<form class="composer" id="chat-form"><input id="chat-input" type="text" autocomplete="off" placeholder="Ask about this store" aria-label="Question">' +
      "<button type=\"submit\">Send</button></form></section>"
    );
  }

  function render() {
    const current = store();
    storeSwitch.querySelectorAll("button").forEach(function (button, index) {
      button.setAttribute("aria-selected", index === state.storeIndex ? "true" : "false");
    });
    document.querySelectorAll("#section-tabs button").forEach(function (button) {
      button.setAttribute("aria-selected", button.dataset.tab === state.tab ? "true" : "false");
    });
    if (state.tab === "revenue") panel.innerHTML = renderRevenue(current);
    if (state.tab === "customers") panel.innerHTML = renderCustomers(current);
    if (state.tab === "authors") panel.innerHTML = renderAuthors(current);
    if (state.tab === "revenue") bindChart(current.daily_revenue);
    bindChat();
    const log = document.getElementById("chat-log");
    if (log) log.scrollTop = log.scrollHeight;
  }

  function bindChat() {
    const form = document.getElementById("chat-form");
    if (!form) return;
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const input = document.getElementById("chat-input");
      ask(input.value);
    });
    panel.querySelectorAll("[data-prompt]").forEach(function (button) {
      button.addEventListener("click", function () { ask(button.dataset.prompt); });
    });
    panel.querySelectorAll("[data-copy]").forEach(function (button) {
      button.addEventListener("click", function () {
        const text = button.getAttribute("data-copy");
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(function () {
            button.textContent = "Copied";
          }, function () {
            button.textContent = text;
          });
        }
      });
    });
  }

  function ask(question) {
    const text = (question || "").trim();
    if (!text) return;
    const history = messages();
    history.push({ role: "user", text: text });
    const reply = state.tab === "authors" ? answerAuthors(store(), text) : answerCustomers(store(), text);
    history.push({ role: "bot", text: reply });
    render();
  }

  desk.stores.forEach(function (item, index) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.store;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", index === 0 ? "true" : "false");
    button.addEventListener("click", function () {
      state.storeIndex = index;
      render();
    });
    storeSwitch.appendChild(button);
  });
  document.querySelectorAll("#section-tabs button").forEach(function (button) {
    button.addEventListener("click", function () {
      state.tab = button.dataset.tab;
      render();
    });
  });
  render();
})();
