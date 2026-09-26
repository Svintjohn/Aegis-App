# Aegis

Milestone escrow for student freelancers. A client locks the budget up front,
the freelancer works against milestones, and money only moves when the client
approves — or automatically, if they go quiet for 14 days.

## Running it

```bash
flutter pub get
flutter run -d chrome        # device_preview wraps it in a phone frame
flutter test
```

## Where things are

```
lib/
  main.dart          app + routes
  theme.dart         colors, type scale, spacing, peso/timeAgo formatters
  data/
    models.dart      Project, Milestone, Message, Notice, DisputeCase
    store.dart       Riverpod notifier — every action lives here, plus seed data
  widgets/
    common.dart      Pressable, AppButton, AppField, AppCard, StatusPill, Avatar…
  screens/           one file per area, grouped where screens share a shape
```

State lives in `Store` (`data/store.dart`). Nothing is persisted yet — restart
and you're back to the seed data. Swapping it for Supabase means replacing the
bodies of the methods in `Store`, not the screens.

## What actually works

Log in → pick a role → everything below responds to real state:

- **Client:** post a project (3-step wizard), lock the budget, approve a
  milestone (money moves to the wallet), request revisions, open an admin case.
- **Freelancer:** browse and apply to jobs, submit work, resubmit after a
  revision request, withdraw the balance.
- Chat, notifications (with unread badge), verification, and settings all read
  and write the same store.
- The role toggle in the app bar switches the whole app between the two views.
