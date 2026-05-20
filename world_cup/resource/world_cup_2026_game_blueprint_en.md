# SYSTEM DESIGN DOCUMENT: INTERNAL COMPANY WORLD CUP 2026 GAME

This document provides a detailed description of the architecture, operational rules, and database structure for the internal World Cup 2026 betting game designed exclusively for company employees. The goal of this project is to boost internal engagement and create an exciting atmosphere throughout the tournament.

---

## 1. GAME INTRODUCTION

* **Core Mechanism:** Employees use a default allocation of electronic currency (Coins) to place bets on the outcomes (Win / Loss / Draw) of matches during the World Cup 2026.
* **Betting Rules:** Every bet placed must be a **multiple of 10** (e.g., 10, 20, 30, 40, 100, 500 Coins...).
* **Attendance/Activity Law (Mandatory Feature):** * Employees **must participate and place at least one bet on EVERY day that a match takes place**.
    * If there is a match scheduled on a specific day and an employee fails to place any bets, the system will automatically **deduct 10% of their total current Coins** at the end of that day.
* **Prize Structure:** After the final match concludes, the system will automatically generate the final leaderboard. The **Top 3 employees with the highest number of Coins** will receive 3 grand prizes from the company.

---

## 2. DETAILED GAME RULES

1.  **Starting Capital:** Each employee will receive a default of **1,000 Coins** upon successful account creation.
2.  **Betting Unit:** Only bet amounts that are multiples of 10 are accepted. The system will block invalid or odd amounts (e.g., 15, 23, 105 Coins).
3.  **Account Verification:** Each employee **can only own 1 unique account**. Accounts are verified via personal Phone Numbers (or Employee IDs) to prevent fraud and multi-accounting.
4.  **Earning Extra Coins (Mission System):** To give employees a chance to make a comeback after losing streaks or coin deductions, they can complete internal PR/communication tasks to earn bonus Coins (e.g., Sharing the match schedule on Facebook, checking in daily at the office, inviting colleagues to join...).

---

## 3. DATABASE INFRASTRUCTURE

The system utilizes a single Relational Database (such as MySQL or PostgreSQL) to manage all game data. Below is the detailed structure of the required tables:

### 3.1. `Users` Table (Employee Information Management)
* `id` (INT, Primary Key, Auto Increment): Unique identifier for the employee.
* `phone` (VARCHAR, Unique): Employee's phone number (used for login and security verification).
* `full_name` (VARCHAR): Employee's full name.
* `current_coins` (INT, Default: 1000): The number of Coins currently owned by the employee.
* `created_at` (TIMESTAMP): Account creation timestamp.

### 3.2. `Matches` Table (Match Information Management)
*(This table can be synchronized or linked directly with the data from your existing World Cup 2026 Website)*
* `match_id` (INT, Primary Key): Unique identifier for the match.
* `team_a` (VARCHAR): Name of Team A.
* `team_b` (VARCHAR): Name of Team B.
* `match_time` (DATETIME): Scheduled time of the match.
* `status` (VARCHAR): Match status (`Not Started`, `Live`, `Finished`).
* `result` (VARCHAR, Nullable): Final outcome of the match (`A_win`, `B_win`, `Draw`).

### 3.3. `Bets` Table (Betting History Management)
* `bet_id` (INT, Primary Key, Auto Increment): Unique identifier for the bet.
* `user_id` (INT, Foreign Key referencing `Users.id`): ID of the employee placing the bet.
* `match_id` (INT, Foreign Key referencing `Matches.match_id`): ID of the match being bet on.
* `bet_choice` (VARCHAR): The selected outcome (`A` - Team A wins, `B` - Team B wins, `DRAW` - Tie).
* `bet_amount` (INT): Placed bet amount (backend must validate that it's a multiple of 10).
* `status` (VARCHAR, Default: 'Pending'): Bet status (`Pending`, `Won`, `Lost`).
* `created_at` (TIMESTAMP): Timestamp when the bet was placed.

### 3.4. `Daily_Check` Table (For the 10% Attendance Penalty Logic)
* `check_id` (INT, Primary Key, Auto Increment): Unique identifier for the daily check record.
* `user_id` (INT, Foreign Key referencing `Users.id`): ID of the employee.
* `date` (DATE): The match day being checked (Format: YYYY-MM-DD).
* `has_voted` (BOOLEAN, Default: FALSE): Status (`TRUE` if the user placed at least one bet on this day, `FALSE` otherwise).

### 3.5. `Mission_Logs` Table (Mission and Reward History Management)
* `log_id` (INT, Primary Key, Auto Increment): Unique identifier for the mission completion log.
* `user_id` (INT, Foreign Key referencing `Users.id`): ID of the employee.
* `mission_type` (VARCHAR): Type of task completed (`share_facebook`, `daily_login`, `invite_friend`).
* `reward_coins` (INT): Number of bonus Coins awarded.
* `completed_at` (TIMESTAMP): Timestamp when the mission was completed.

---

## 4. SYSTEM LOGIC & OPERATION

To ensure the system runs automatically and accurately, the development team needs to implement the following core logics:

### 4.1. 10% Attendance Penalty Logic (Daily Cron Job)
* **Action:** Set up a **Cron Job** that runs automatically at **23:59:00 daily** (or 00:01:00 on the following day).
* **Processing Workflow:**
    1. Check if there are any matches scheduled for today in the `Matches` table. If there are no matches, skip the penalty check.
    2. If there are matches, fetch the complete list of employees from the `Users` table.
    3. For each employee, verify if they have any active records in the `Bets` table for today's matches.
    4. If they **HAVE NOT** placed any bets (`has_voted` = FALSE):
       * Calculate the penalty: `Penalty = current_coins * 0.1` (Note: You can round this to the nearest integer or multiple of 10).
       * Update the coin balance: `current_coins = current_coins - Penalty`.
       * Log the penalty transaction so the employee can review why their coins were deducted.

### 4.2. Anti-Cheat & Verification Logic
* **Unique Constraints:** Set a `UNIQUE CONSTRAINT` on the `phone` field in the database to prevent a single phone number from registering multiple accounts.
* **HR List Synchronization (Recommended):** Maintain an isolated table containing official Employee IDs + Phone Numbers provided by the HR department. When an employee registers, cross-check the inputs against this table; only grant the default 1,000 Coins if a verified match is found.

### 4.3. Social Media Sharing Logic (Facebook Share)
* Due to strict privacy policies within the Facebook API, directly verifying a user's private wall post status programmatically is restricted. The optimal workaround is:
    * When the employee clicks "Share on Facebook", use JavaScript to open a new pop-up window containing the Facebook share URL dialog.
    * Use an event listener to detect when the pop-up window is closed, or set a countdown timeout of approximately 3 - 5 seconds.
    * After that duration, display a "Mission Completed" notification, trigger the backend API to credit the `reward_coins` into the `Users` table, and write a record into `Mission_Logs`.

---

## 5. UI/UX INTEGRATION SCENARIOS FOR THE EXISTING WEBSITE

Leveraging your existing World Cup 2026 website, you only need to build out the following front-end interface modules:

1.  **User Status Widget (Header):** Displayed at the top right corner post-login: [ Employee Name | Wallet: **1,250 Coins** | Current Rank: **#15** ].
2.  **Betting Modal:** When clicking on any match from the schedule list, a modal pops up allowing users to select:
    * Options: [Team A Wins] [Draw] [Team B Wins]
    * An input field for the coin amount (implement `+10`, `+50`, `+100` step buttons to visually guide the user into entering valid multiples of 10).
3.  **Company Leaderboard Tab:** Displays a real-time ranking list of all participating employees. Highlight the **Top 3** leaders using Gold, Silver, and Bronze trophy/medal icons to spark competitive engagement.
4.  **Mission Hub:** A dedicated area where employees can access daily tasks to replenish their coin balances and keep playing.

---
*This document is prepared for direct hand-off to system architects and backend/frontend developers.*
