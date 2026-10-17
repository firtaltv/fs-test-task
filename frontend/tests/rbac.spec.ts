import { expect, type Page, test } from "@playwright/test"
import type { Role } from "../src/client"
import { firstSuperuser, firstSuperuserPassword } from "./config.ts"
import { createUserWithRole } from "./utils/adminApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

const logInAs = async (page: Page, role: Role) => {
  const email = randomEmail()
  const password = randomPassword()
  await createUserWithRole({ email, password, role })
  await logInUser(page, email, password)
  return email
}

test.describe("Navigation", () => {
  test("Member doesn't see the Admin or Metrics links", async ({ page }) => {
    const email = await logInAs(page, "member")

    // Wait for /users/me: before it resolves the gated links are hidden for
    // everyone, so the absence checks below would pass vacuously
    await expect(page.getByText(email).first()).toBeVisible()
    await expect(page.getByRole("link", { name: "Items" })).toBeVisible()
    await expect(page.getByRole("link", { name: "Admin" })).toHaveCount(0)
    await expect(page.getByRole("link", { name: "Metrics" })).toHaveCount(0)
  })

  test("Manager sees the Admin and Metrics links", async ({ page }) => {
    await logInAs(page, "manager")

    await expect(page.getByRole("link", { name: "Admin" })).toBeVisible()
    await expect(page.getByRole("link", { name: "Metrics" })).toBeVisible()
  })
})

test.describe("Users page", () => {
  test("Manager sees the users list without Add, Edit or Delete", async ({
    page,
  }) => {
    const memberEmail = randomEmail()
    await createUserWithRole({
      email: memberEmail,
      password: randomPassword(),
      role: "member",
    })
    await logInAs(page, "manager")

    await page.goto("/admin")

    await expect(page.getByRole("heading", { name: "Users" })).toBeVisible()
    const memberRow = page.getByRole("row").filter({ hasText: memberEmail })
    await expect(memberRow).toBeVisible()
    await expect(memberRow.getByText("Member", { exact: true })).toBeVisible()
    // No actions menu on any row, and no Add User button
    await expect(page.getByRole("table").getByRole("button")).toHaveCount(0)
    await expect(page.getByRole("button", { name: "Add User" })).toHaveCount(0)
  })

  test("Admin can assign a role when creating a user", async ({ page }) => {
    await logInUser(page, firstSuperuser, firstSuperuserPassword)
    await page.goto("/admin")

    const email = randomEmail()
    const password = randomPassword()
    await page.getByRole("button", { name: "Add User" }).click()
    await page.getByPlaceholder("Email").fill(email)
    await page.getByPlaceholder("Password").first().fill(password)
    await page.getByPlaceholder("Password").last().fill(password)
    await page.getByLabel("Role").click()
    await page.getByRole("option", { name: "Manager" }).click()
    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("User created successfully")).toBeVisible()
    const userRow = page.getByRole("row").filter({ hasText: email })
    await expect(userRow.getByText("Manager", { exact: true })).toBeVisible()
  })
})

test.describe("Direct navigation", () => {
  for (const path of ["/admin", "/metrics"]) {
    test(`Member opening ${path} directly sees Access denied`, async ({
      page,
    }) => {
      await logInAs(page, "member")

      await page.goto(path)
      await expect(page.getByTestId("access-denied")).toBeVisible()
      await expect(page).toHaveURL(path)

      // Survives a hard refresh, when the current user isn't cached yet
      await page.reload()
      await expect(page.getByTestId("access-denied")).toBeVisible()

      await page.getByRole("link", { name: "Back to dashboard" }).click()
      await expect(page).toHaveURL("/")
    })
  }

  test("Manager can open /metrics directly and sees the stats", async ({
    page,
  }) => {
    await logInAs(page, "manager")

    await page.goto("/metrics")

    await expect(page.getByRole("heading", { name: "Metrics" })).toBeVisible()
    await expect(page.getByTestId("stat-card")).toHaveCount(5)
    await expect(page.getByText("Total users")).toBeVisible()
  })
})

test.describe("Own profile", () => {
  test("Shows the role read-only, with no way to change it", async ({
    page,
  }) => {
    await logInAs(page, "manager")

    await page.goto("/settings")
    await expect(page.getByTestId("current-role")).toHaveText("Manager")
    await page.getByRole("button", { name: "Edit" }).click()
    await expect(page.getByRole("combobox")).toHaveCount(0)
  })
})

test.describe("Invariants", () => {
  test("Admin deleting their own account sees why and stays signed in", async ({
    page,
  }) => {
    await logInAs(page, "admin")

    await page.goto("/settings")
    await page.getByRole("tab", { name: "Danger zone" }).click()
    await page.getByRole("button", { name: "Delete Account" }).click()
    await page.getByRole("button", { name: "Delete", exact: true }).click()

    // 409: the backend's reason, not the generic permission toast. Read the
    // toast once: a retrying "not visible" assertion would pass as soon as
    // the toast auto-dismisses.
    const toast = page
      .locator("[data-sonner-toast]")
      .filter({ hasText: "Admins are not allowed to delete themselves" })
    await expect(toast).toBeVisible()
    expect(await toast.innerText()).not.toContain("permission")
    await page.reload()
    await expect(page).toHaveURL("/settings")
    await expect(page.getByTestId("current-role")).toHaveText("Admin")
  })
})
