var data = window.DESK.stores;
var storeIndex = 0;
var tab = "revenue";
var chats = {};

function money(cents) {
  return "$" + (cents / 100).toFixed(2);
}

function ids(list) {
  return "[" + list.join(", ") + "]";
}

function names(list) {
  return list.join(", ");
}

function current() {
  return data[storeIndex];
}

function chatKey() {
  return storeIndex + tab;
}

function answer(question) {
  var store = current();
  var q = question.toLowerCase();
  if (tab === "users") {
    if (q.indexOf("best") !== -1 || q.indexOf("buyer") !== -1 || q.indexOf("spent") !== -1) {
      var buyer = store.best_buyers[0];
      return "Best buyer: " + ids(buyer.ids) + "\nNames: " + names(buyer.names) + "\nSpend: " + money(buyer.spend_cents);
    }
    if (q.indexOf("how many") !== -1 || q.indexOf("unique") !== -1 || q.indexOf("number") !== -1) {
      return "Unique users: " + store.unique_users;
    }
    if (q.indexOf("how") !== -1 || q.indexOf("match") !== -1 || q.indexOf("alias") !== -1 || q.indexOf("same") !== -1) {
      return "Rows are the same person if only one of name, address, phone or email is different. " + store.store + " has " + store.unique_users + " people from " + store.audit.users_used + " rows.";
    }
    return "Unique users: " + store.unique_users;
  }
  if (q.indexOf("popular") !== -1 || q.indexOf("most") !== -1 || q.indexOf("sold") !== -1) {
    var top = store.most_popular[0];
    return names(top.authors) + "\nCopies: " + top.copies;
  }
  if (q.indexOf("what") !== -1 || q.indexOf("set") !== -1 && q.indexOf("how many") === -1) {
    return "An author set is the names written on one book. John and Paul together are a different set from John alone.";
  }
  return "Unique author sets: " + store.unique_author_sets;
}

function render() {
  var buttons = document.querySelectorAll("#stores button, #tabs button");
  for (var i = 0; i < buttons.length; i++) {
    var b = buttons[i];
    if (b.parentNode.id === "stores") b.className = b.dataset.i === String(storeIndex) ? "on" : "";
    else b.className = b.dataset.tab === tab ? "on" : "";
  }
  var store = current();
  var html = "";
  if (tab === "revenue") {
    html += "<h2>Top 5 days</h2><table><tr><th>Date</th><th>Revenue</th></tr>";
    for (var d = 0; d < store.top5_days.length; d++) {
      html += "<tr><td>" + store.top5_days[d].date + "</td><td>" + money(store.top5_days[d].cents) + "</td></tr>";
    }
    html += "</table>";
    html += "<h2>Daily revenue</h2>";
    html += '<img src="charts/' + store.store.toLowerCase() + '_daily_revenue.png" alt="daily revenue">';
  } else if (tab === "users") {
    var buyer = store.best_buyers[0];
    html += "<p>Unique users: <b>" + store.unique_users + "</b></p>";
    html += "<p>Best buyer: <b>" + ids(buyer.ids) + "</b></p>";
    html += "<p>Names: " + names(buyer.names) + "</p>";
    html += chatBox("Users");
  } else {
    var top = store.most_popular[0];
    html += "<p>Unique author sets: <b>" + store.unique_author_sets + "</b></p>";
    html += "<p>Most popular: <b>" + names(top.authors) + "</b></p>";
    html += "<p>Copies sold: " + top.copies + "</p>";
    html += chatBox("Authors");
  }
  document.getElementById("panel").innerHTML = html;
  var form = document.getElementById("chat-form");
  if (form) {
    form.onsubmit = function (event) {
      event.preventDefault();
      var input = document.getElementById("chat-input");
      var text = input.value.trim();
      if (!text) return;
      var key = chatKey();
      if (!chats[key]) chats[key] = [];
      chats[key].push("You: " + text);
      chats[key].push(answer(text));
      input.value = "";
      render();
    };
  }
}

function chatBox(title) {
  var key = chatKey();
  var lines = chats[key] || ["Ask about " + title.toLowerCase() + "."];
  var box = '<div class="chat"><b>' + title + "</b><div id=\"log\">" + lines.join("\n\n") + "</div>";
  box += '<form id="chat-form"><input id="chat-input" type="text"> <button type="submit">Send</button></form></div>';
  return box;
}

var storeBox = document.getElementById("stores");
for (var i = 0; i < data.length; i++) {
  var button = document.createElement("button");
  button.type = "button";
  button.dataset.i = String(i);
  button.textContent = data[i].store;
  button.onclick = function () {
    storeIndex = Number(this.dataset.i);
    render();
  };
  storeBox.appendChild(button);
}
var tabButtons = document.querySelectorAll("#tabs button");
for (var t = 0; t < tabButtons.length; t++) {
  tabButtons[t].onclick = function () {
    tab = this.dataset.tab;
    render();
  };
}
render();
