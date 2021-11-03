---
book:
  author: Daniel Stenberg
  cover_image_url: https://i.gr-assets.com/images/S/compressed.photo.goodreads.com/books/1547455205l/43560466._SX98_.jpg
  goodreads: '43560466'
  pages: 68
  publication_year: 2018
  source: https://http3-explained.haxx.se/en/
  spine_color: '#e38e2a'
  tags:
  - nonfiction
  - tech
  title: HTTP/3 explained
plan:
  date_added: '2020-01-11'
related_books:
- book: michael-w-lucas/ssh-mastery
  text: More good technical networking explanations with a cultural component.
review:
  date_read:
  - 2020-01-12
  rating: 4
  tldr: An overview over HTTP/3 by the developer of curl. Fairly short and informative,
    and includes a helpful amount of history and reasoning. A good way to find out
    if and where you want to dive deeper into the topic.
social:
  mastodon:
    datetime: 2020-06-27 11:08:08.977181
    id: '104415159176876375'
    in_reply_to: 104415114120449037
    text: '5/ HTTP/3 explained by Daniel Stenberg. An overview over HTTP/3 by the
      developer of curl. Fairly short and informative, and includes a helpful amount
      of history and reasoning. A good way to find out if and where you want to dive
      deeper into the topic.

      https://books.rixx.de/reviews/2020/http-3-explained/ #rixxReads'
  number: 5
  twitter:
    datetime: 2020-06-27 11:08:08.651293
    id: '1276804495943405569'
    in_reply_to: 1276801612271382528
    text: '5/ HTTP/3 explained by Daniel Stenberg. An overview over HTTP/3 by the
      developer of curl. Fairly short and informative, and includes a helpful amount
      of history and reasoning. A good way to find out if and where you want to dive
      deeper into the topic.

      https://books.rixx.de/reviews/2020/http-3-explained/'
---

HTTP/3 Explained is a little free booklet by curl developer Daniel Stenberg explaining the principles and history behind HTTP/3. I liked the inclusion of recent history and explanation of discussions in the working groups. There is also some frank discussion of potential downsides in terms of security, performance, and adaptability, but usually there is one argument presented per point, so I had the impression that my opinion was being nudged (because of the lack of differing arguments). This is mostly due to the booklets short texts that don't expand much upon anything. Both the writing and the general structure are a bit rough around the edges.

This book is definitely worth the read to get a general impression of the structure of HTTP/3, where it operates, and what its governing principles are. I now have a feeling for its complexity, but I can't say that "reimplement TCP realm logic on UDP" has completely inspired my trust. Some of the performance shortcuts seem like vulns/side channels waiting to be exploited. We'll get real life data soon-ish though, since the nginx implementation is work in progress already, and clients are also under way and/or implemented.

I read up a bit on the meeting minutes, and some of the most debated topics have been skipped, such as the functioning of load balancers (surely interesting for most users). Functionally, a load balancer is one of those tampering middleboxes the protocol means to include, only that it's *trusted*. I wish this had been mentioned in the book.
