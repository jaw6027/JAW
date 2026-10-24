# Your nail art journal: a short guide

## 1. Log in and publish a design

Go to `/owner/` on the website. For the development preview, read your private username and password in `data/local-owner-access.txt`. Do not share that file. Production uses a separately created owner account with a long, unique password.

Choose **Create a design**. Add a title, description, optional instructions (one step per line), and a color, style, and occasion for gallery filters. The shareable address fills from the title; keep it unchanged after sharing.

Under **Photos**, select files from your phone or computer. JPEG, PNG, and WebP are supported; convert HEIC photos to JPEG first. Each photo must be below 10 MB and 40 megapixels. The website resizes photos, saves WebP versions, and removes camera metadata. Describe each image for visitors using screen readers. Lower position numbers appear first; tick **Is cover** for your main photo. Choose **Add another Photo** for more images.

Keep the status as **Draft** and choose **Save and continue editing**. Use **Preview design** to check the page. Only the logged-in owner can see drafts or draft photos. Choose **Published** and save to make it public. Select **Notify subscribers** before the first publication if you want an announcement. Switch back to Draft to hide a design. Open the design and choose Delete to remove it.

Use **Edit brand & biography** to change your brand name, biography, social links, and featured design. Only a published featured design can appear on the homepage. Petal & Polish is simply a starting name to replace.

## 2. Add supplies and purchase links

Under **Supplies**, enter the product name, brand, shade or color, and optional notes. Paste the real **https://** retailer product link into Purchase URL. Visitors see **Buy from retailer**, opening the retailer separately. Leave the link blank when unavailable. Select **Affiliate** if you may receive a commission; a disclosure appears automatically. Check real purchase links before publishing. The samples intentionally have no purchase URLs.

## 3. How subscribers and notifications work

Visitors enter an address and agree to receive emails. After you connect Resend, the site sends a confirmation link valid for 48 hours. The visitor opens it and presses **Confirm my subscription**. This extra button avoids email scanners automatically subscribing people. No visitor account is required.

When you first publish a real design with **Notify subscribers** checked, one email per active, confirmed subscriber enters the queue. The background worker sends the title, cover image, short description, page link, and unsubscribe link. Later edits or republishing never send a second announcement. Publishing without the checkbox does not send a delayed announcement later. Samples never send notifications.

The studio shows queued and provider-accepted counts. “Accepted” means Resend accepted the message, not guaranteed inbox delivery. Check its dashboard for delivery and bounces. Every update includes an unsubscribe page with a confirmation button. Unsubscribed addresses stop receiving queued updates too. Subscriber addresses remain private.

If a delivery result stays uncertain for over 23 hours, retries stop to avoid duplicates. Ask a technical helper to inspect Resend logs and reconcile it; do not simply clear sent records. This setup is for a small journal, not a bulk marketing platform. Monitor provider requirements as your audience grows.

**Without email credentials, subscriptions stay in clearly labeled preview mode. Addresses are not saved and no email is sent.** The studio email preview is visual only.

## 4. What you need to launch

- Hosting with a persistent disk and support for the background worker. Nothing has been purchased or publicly deployed.
- A domain name if you want your own website address.
- A Resend account, verified sending domain, API key, and sender address. Add the DNS records Resend provides. Store the key privately in your host's `RESEND_API_KEY` setting and the verified sender in `EMAIL_FROM`. Never paste secrets into code or chat.
- A private production `DJANGO_SECRET_KEY`, plus the real site URL and allowed domain settings from the deployment guide.
- Your own photos, biography, social links, and actual retailer links. Review the starter privacy notice and add a contact method and retention period before launch.

## 5. Deploy and connect your domain

Give [DEPLOYMENT.md](DEPLOYMENT.md) to your technical helper. It includes Docker, durable storage, the email worker, and optional HTTPS. The domain's DNS A record points to your hosting server; application settings must match that domain.

Approve costs and the public launch before enabling the public HTTPS service. Before announcing the site, test with an email address you own: subscribe, confirm, receive one notification, edit the design without a duplicate, then unsubscribe. These real-service checks require your accounts. Confirm backups can be restored before entrusting the site with original work.
