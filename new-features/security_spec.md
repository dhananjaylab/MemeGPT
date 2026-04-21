# Security Specification for MemeGPT

## Data Invariants
1. A user profile must match the authenticated UID.
2. A meme must have a valid template ID.
3. Meme text must be an array of strings.
4. Timestamps must be server-generated.

## The Dirty Dozen (Attack Vectors)
1. **Identity Spoofing**: Attempting to create a user profile with a different UID.
2. **Resource Poisoning**: Injecting 1MB strings into meme text.
3. **Shadow Update**: Adding `isAdmin: true` to a user profile.
4. **Orphaned Writes**: Creating a meme with a non-existent template ID.
5. **PII Leak**: Authenticated user reading another user's profile info.
6. **Query Scraping**: Listing all memes without filtering for public status.
7. **Rate Limit Bypass**: Rapidly incrementing like counts.
8. **Template Hijack**: Authenticated user modifying system templates.
9. **Fake Verification**: Setting `email_verified: true` in the DB when the token says false.
10. **State Shortcutting**: Manually setting `share_count` to a massive number.
11. **ID Poisoning**: Using paths like `templates/../../../etc/passwd` (well, simplified version).
12. **Anonymous Write**: Attempting to create a meme without being signed in.
