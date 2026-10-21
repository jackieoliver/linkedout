const assert = require("node:assert");
const test = require("node:test");
const { LINKEDOUT_DEFAULTS: D, linkedoutClassifyNotification: classify, linkedoutHideConversation: hideConv } = require("../rules.js");

const hideMode = { ...D, notificationMode: "hide" };

test("keep mode keeps things that involve you", () => {
  assert.equal(classify("Sam Lee commented on your post: nice work", D), "keep");
  assert.equal(classify("Ana  Ruiz\nmentioned you in a comment", D), "keep");
  assert.equal(classify("Kai accepted your invitation to connect", D), "keep");
});

test("keep mode hides everything else", () => {
  assert.equal(classify("Your profile was viewed by 12 people", D), "hide");
  assert.equal(classify("You appeared in 40 searches this week", D), "hide");
  assert.equal(classify("Some new kind of notification", D), "hide");
});

test("sponsored always hides, even when a keep phrase matches", () => {
  assert.equal(classify("Promoted · Acme commented on your industry", D), "hide");
  assert.equal(classify("Sponsored\nAcme mentioned you", hideMode), "hide");
});

test("hide mode shows unknown notifications and hides listed ones", () => {
  assert.equal(classify("Some new kind of notification", hideMode), "keep");
  assert.equal(classify("3 people viewed your profile", hideMode), "hide");
  assert.equal(classify("Jo posted for the first time in a while", hideMode), "hide");
});

test("conversation rows", () => {
  assert.equal(hideConv(["Acme Corp", "Sponsored", "Oct 3"], D), true);
  assert.equal(hideConv(["Recruiter", "InMail"], D), false);
  assert.equal(hideConv(["Recruiter", "InMail"], { ...D, hideInMail: true }), true);
  assert.equal(hideConv(["Sam", "Sponsored by nobody, just a word"], D), false);
  assert.equal(hideConv(["Acme", "Sponsored"], { ...D, hideSponsoredMessages: false }), false);
});

// Real notification texts (names changed), 2026-10-21 (all noise).
const REAL_NOISE = [
  "Senior Software Engineer at Acme Pay and 5 other recommendations for you. View jobs 6m",
  "Sam Park posted: We asked an agent to log 40 outreach messages",
  "Suggested for you: I’m hiring a Chief of Staff",
  "You appeared in 27 searches this week. Premium benefit 5h",
  "12 people viewed your profile: See who it is with Premium.",
  "Robin Hale reposted Jo Lind's post: Very little",
  "💌 You've got an invite. Max Cole finished Wend. Your move 23h",
  "Lee Grant commented on Ana Ruiz’s post: shows",
  "Kim Ho, Pat Doe and 2 other connections reacted to a post: What a SHIP!",
  "Reminder: You're eligible to add a verification to your profile",
  "Director of Research Services Chris Moe could be your",
  "New from Acme Ratings in Private Credit Market Watch",
  "You may want to connect with Taylor Quinn, based on your recent",
  "Celebrate Dana Burke’s recent birthday on Oct 13.",
  "People are engaging with Mika Sato’s post",
  "This post by Jordan Lee is popular with your network",
];

test("real noise is hidden in both modes", () => {
  for (const t of REAL_NOISE) {
    assert.equal(classify(t, D), "hide", t);
    assert.equal(classify(t, hideMode), "hide", t);
  }
});

test("hide-mode phrases don't swallow notifications about you", () => {
  assert.equal(classify("Sam commented on your post: great", hideMode), "keep");
  assert.equal(classify("Ana reposted your post", hideMode), "keep");
});

test("real sponsored conversation row", () => {
  assert.equal(hideConv(["Brand Sender", "2:03 PM", "Sponsored", "•"], D), true);
  assert.equal(hideConv(["Status is offline", "Alex Rivera", "Sep 3"], D), false);
});
