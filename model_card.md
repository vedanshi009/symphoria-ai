# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  
  **Symphoria 1.0**  

---

## 2. Intended Use  

Symphoria is a simple music recommender designed to suggest songs based on a user’s mood and listening taste. It generates ranked song recommendations by analyzing how well each track matches the user’s current “listening state.” The goal is to simulate how modern music apps personalize playlists, but in a transparent and explainable way.

This system is mainly built for **classroom exploration and learning**, not real-world production use. It helps demonstrate how recommendation systems think, how bias can appear, and how different rules affect results.

### What it recommends
- Songs that match a user’s mood (like focused, relaxed, or energetic)
- Music that fits an energy range (calm vs high-energy listening)
- Tracks similar in genre or nearby genres
- Songs that match emotional tone and listening style

### What it assumes about users
- Users have a fairly stable “listening mood” at a time
- Mood, energy, and genre are enough to describe taste
- Preferences can be expressed using simple numeric ranges and labels
- Similar features mean better listening experience 

---

## 3. How the Model Works  

Symphoria looks at each song and asks:  
**“How well does this fit what the user is feeling right now?”**

To answer this, it checks:

- 🎧 **Genre** → Does the song match or closely relate to the user’s favorite genre?
- ⚡ **Energy** → Is the song too calm, too intense, or within the preferred energy range?
- 😊 **Mood** → Does the emotional tone match the user’s current mood context?
- 🌊 **Valence & Acousticness** → Does the song feel happy/sad and more acoustic or electronic?
- 💃 **Danceability & Tempo** → Does the rhythm match the expected listening pace?

Each of these contributes a small score. The system adds them together to form a final rating for each song.

It then:
- scores all songs
- compares them
- sorts them from best match to weakest match
- returns the top results

---

## 4. Data  

The system uses a small dataset of 20 songs stored in a CSV file. Each song includes features like genre, mood, energy, tempo, valence, danceability, and acousticness.

The dataset includes a mix of genres such as pop, lofi, rock, hip-hop-inspired styles, electronic, indie, and ambient. It also covers different moods like happy, chill, intense, dreamy, nostalgic, and moody, which helps simulate different listening situations.

One limitation is that the dataset does not fully capture the complexity of real musical taste. It is missing deeper cultural context, lyrics, artist popularity, and sub-genre richness. Some emotional states (like anxiety, motivation, or calm focus transitions) are also not fully represented.

---

## 5. Strengths  

The system works well for users with clear and structured preferences, such as:
- Chill / lofi listeners who prefer calm, low-energy music
- High-energy pop or workout-style users
- Users with a clear mood like “focused,” “relaxed,” or “intense”

It successfully captures patterns between energy, mood, and genre, and often places songs with matching emotional tone and energy levels at the top of the list. For example, low-energy acoustic songs consistently appear for relaxed users, while high-energy electronic or pop songs rank higher for energetic users.

The scoring system also matches intuition in many cases, especially when mood and energy align. Users generally receive playlists that “feel right” for the situation, showing that the layered scoring approach is working as intended.

One strong point is that the system produces explainable recommendations, making it easy to understand why a song was chosen instead of acting like a black box.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

During testing, I noticed that the system relies too heavily on energy alignment, which strongly affects rankings even when user preferences are unclear or conflicting. This sometimes causes similar songs to appear for very different listeners. Because the feature weights are fixed, the recommender does not fully adapt to uncertain user intent. In the future, the system could adjust weights dynamically based on how specific the user’s preferences are.


During experimentation, several possible filter bubbles and scoring biases were identified in the current recommendation system design.

### 1. Energy Dominance Bias
Energy alignment contributes the largest portion of the score (up to 0.22) and also indirectly affects rhythm expectations and tempo penalties. Because multiple layers depend on energy, users with extreme energy preferences tend to receive very similar recommendations repeatedly. This can create an **energy-driven filter bubble**, where songs outside the preferred energy band rarely surface.

### 2. Acousticness Always Influences Scoring
Acoustic similarity is always rewarded, even when the user does not explicitly state an acoustic preference. This means acoustic songs may consistently rank higher simply because they numerically align with the target value, potentially biasing recommendations toward certain production styles.

### 3. Mood Vocabulary Coverage Bias
Mood matching relies on a small predefined set of mood families. Songs with moods not included in these mappings (e.g., *dreamy*, *nostalgic*, *chaotic*) receive no partial credit unless there is an exact match. This can unintentionally disadvantage genres or emotional styles that fall outside the curated mood taxonomy.

### 4. Genre Anchoring Effect
The scoring system explicitly rewards favorite genres and neighboring genres. While helpful for personalization, this reinforcement can reduce exploration by repeatedly recommending familiar genres instead of introducing diverse musical styles.

### 5. Fixed Weight Rigidity
All scoring weights are static and identical for every user profile. Users with conflicting or ambiguous preferences (for example, high energy but sad mood targets) are forced into the same weighting scheme, which may produce unexpected or unintuitive rankings.

### 6. Tempo Penalty Compounding
Tempo penalties are multiplicative and applied after additive scoring. This can disproportionately suppress otherwise strong matches when BPM slightly deviates from expectations, potentially excluding stylistically valid songs.

---

Overall, the current system favors **consistency over discovery**, which improves explainability but increases the risk of recommendation loops and reduced musical diversity. Future improvements could include adaptive weighting, broader mood embeddings, or controlled randomness to encourage exploration.

---

## 7. Evaluation  

- I tested multiple user profiles including **High-Energy Pop**, **Chill Lofi**, **Deep Intense Rock**, and an **edge case profile** with conflicting preferences (high energy but sad mood).  
- The High-Energy Pop profile consistently ranked energetic songs higher, while the Chill Lofi profile shifted toward slower, acoustic tracks. This showed the system responds correctly to energy and acoustic preferences.  
- Comparing profiles helped verify logic: when energy increased, rhythm and tempo also became faster, which made sense because energetic listeners usually prefer more movement in music.  
- One surprise was that some songs appeared across different profiles because strong mood matches sometimes outweighed genre differences.  
- The conflicting preference profile (high energy + sad mood) produced mixed results, revealing that the system sometimes prioritizes energy over emotional tone.  
- I also manually compared rankings before and after changing weights to confirm that recommendations changed in predictable ways.  
- Overall, the recommender behaved logically, but testing showed that strong features like energy can dominate results and reduce diversity.

---

## 8. Future Work  

Some ideas that I can implement in the future:


Add more user preferences such as time of day, activity (studying, gym, relaxing), or listening history to make recommendations more personal.  
- Increase diversity in top results so recommendations do not feel repetitive or dominated by one genre or artist.  
- Better handle complex or conflicting tastes by balancing multiple features instead of letting one factor (like energy) dominate the score.  
- Introduce learning from feedback so the system improves over time based on user reactions.
---

## 9. Personal Reflection  

Some learnings from the project:

- I learned that small design decisions can lead to large variations in recommendations. Adding more meaningful factors helps make the system smarter and more realistic.
- I realized how easily biases can be introduced through scoring weights, dataset distribution, or rule design.
- I also learned that music recommendation systems are not just matching songs to genres. They balance user psychology, listening context, and trade-offs between accuracy, diversity, and fairness.
