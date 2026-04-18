import { Component, computed, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { ScrawlCardComponent, ScrawlAction, ReplyAction, ReplyPayload, NestedReplyPayload } from '../components/scrawl-card/scrawl-card.component';
import { AuthService } from '../services/auth.service';
import { UserService } from '../services/user.service';
import { PostService, ApiPost } from '../services/post.service';
import { Scrawl } from '../models/scrawl.models';

type ProfileTab = 'scrawls' | 'rescrawls' | 'saved' | 'mood';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, ScrawlCardComponent],
  templateUrl: './profile.html',
  styleUrl: './profile.css'
})
export class ProfileComponent implements OnInit, OnDestroy {
  private route        = inject(ActivatedRoute);
  private authService  = inject(AuthService);
  private userService  = inject(UserService);
  private postService  = inject(PostService);

  private routeSub?: Subscription;

  // ── Resolved username (from route param, or falls back to current user) ───
  readonly profileUsername = signal<string>('');

  /** True when viewing your own profile */
  readonly isOwnProfile = computed(() =>
    this.authService.isCurrentUser(this.profileUsername())
  );

  // ── Displayed user data (merged from services) ────────────────────────────
  readonly displayUser = computed(() => {
    const username = this.profileUsername();
    if (!username) return null;

    if (this.isOwnProfile()) {
      // Own profile: use AuthService (source of truth for own data)
      const u = this.authService.currentUser();
      if (!u) return null;
      const initials = u.displayName.split(' ').map(w => w[0] || '').join('').slice(0, 2).toUpperCase();
      return {
        username:    u.username,
        displayName: u.displayName,
        first_name:  u.first_name,
        last_name:   u.last_name,
        studentId:   u.studentId,
        email:       u.email,
        phone:       u.phone,
        bio:         u.bio,
        avatar:      u.avatar || initials,
        faculty:     u.faculty || '',
      };
    } else {
      // Other user: lookup in UserService
      const p = this.userService.getProfile(username);
      return p
        ? { username: p.username, displayName: p.displayName, studentId: p.studentId,
            email: p.email, phone: p.phone, bio: p.bio, avatar: p.avatar, faculty: p.faculty }
        : null;
    }
  });

  // ── Follow system (only relevant for other profiles) ──────────────────────
  readonly isFollowed = computed(() =>
    this.userService.isFollowing(this.profileUsername())
  );

  readonly followersCount = computed(() => 0);

  readonly followingCount = computed(() => 0);

  toggleFollow(): void {
    if (!this.isOwnProfile()) {
      this.userService.toggleFollow(this.profileUsername());
    }
  }

  // ── Bio editing (own profile only) ────────────────────────────────────────
  editBio = signal('');
  isEditingBio = signal(false);

  startEditBio(): void {
    if (!this.isOwnProfile()) return;
    const u = this.authService.currentUser();
    this.editBio.set(u ? u.bio : '');
    this.isEditingBio.set(true);
  }

  saveBio(): void {
    const newBio = this.editBio();
    // Optimistically update UI
    this.authService.updateBio(newBio);
    this.isEditingBio.set(false);
    // Persist to backend
    this.authService.updateProfile({ bio: newBio }).subscribe({
      error: () => console.error('Failed to save bio')
    });
  }

  cancelEditBio(): void {
    this.isEditingBio.set(false);
  }

  // ── Avatar editing (own profile only) ──────────────────────────────────────
  onAvatarFileSelected(event: Event): void {
    if (!this.isOwnProfile()) return;
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('avatar', file);

    this.authService.updateProfile(formData).subscribe({
      error: () => console.error('Failed to upload avatar')
    });
  }

  // ── Tabs ──────────────────────────────────────────────────────────────────
  activeTab = signal<ProfileTab>('scrawls');
  setTab(tab: ProfileTab): void {
    this.activeTab.set(tab);
    if (!this.isOwnProfile()) return;
    if (tab === 'saved') this.loadSavedPosts();
    if (tab === 'rescrawls') this.loadRescrawledPosts();
  }

  // ── Mood history ─────────────────────────────────────────────────────────
  happy = computed(() => this.calculateMoodCount('happy'));
  sad   = computed(() => this.calculateMoodCount('sad'));
  angry = computed(() => this.calculateMoodCount('angry'));
  chill = computed(() => this.calculateMoodCount('chill'));

  // ── Own posts (local, only used for own profile) ──────────────────────────
  private readonly ownPostsData: Scrawl[] = [];

  localOwnPosts = signal<Scrawl[]>([]);

  // Other-user sample posts (shown when viewing other profiles)
  readonly otherUserPostsData: Record<string, Scrawl[]> = {};

  localOtherPosts = signal<Scrawl[]>([]);

  // ── Feed posts (rescrawled & saved — only shown on OWN profile) ───────────
  readonly savedPostsData = signal<Scrawl[]>([]);
  readonly rescrawledPostsData = signal<Scrawl[]>([]);
  readonly rescrawledPosts = computed(() => this.rescrawledPostsData());
  readonly savedPosts = computed(() => this.savedPostsData());
  readonly replyInputOpenByPost = signal<Record<string, boolean>>({});
  readonly repliesOpenByPost = signal<Record<string, boolean>>({});
  readonly repliesByPost = signal<Record<string, Scrawl['replies']>>({});

  // ── Stats ─────────────────────────────────────────────────────────────────
  readonly scrawlsCount   = computed(() => this.localOwnPosts().length);
  readonly totalLikes     = computed(() => this.localOwnPosts().reduce((acc, p) => acc + p.likeCount, 0));
  readonly rescrawlsCount = computed(() => this.rescrawledPosts().length);
  readonly savedCount     = computed(() => this.savedPosts().length);

  // ── Lifecycle ─────────────────────────────────────────────────────────────
  ngOnInit(): void {
    this.routeSub = this.route.params.subscribe(params => {
      const paramUsername = params['id'] || params['username'] || '';
      const resolved = paramUsername || (this.authService.currentUser()?.username ?? '');
      this.profileUsername.set(resolved);

      // Reset tab on navigation
      this.activeTab.set('scrawls');
      this.isEditingBio.set(false);

      const currentUser = this.authService.currentUser();

      if (this.authService.isCurrentUser(resolved) && currentUser?.id) {
        // Load own posts from API
        this.postService.loadMyPosts().subscribe({
          next: (posts) => this.localOwnPosts.set(posts.map(p => this._mapApiPost(p))),
          error: (err) => console.error('Failed to load own posts:', err)
        });
        this.loadSavedPosts();
        this.loadRescrawledPosts();
      } else {
        // Clear other-user posts (no external user profile API yet)
        this.localOtherPosts.set([]);
        this.savedPostsData.set([]);
        this.rescrawledPostsData.set([]);
      }
    });
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  getInitial(): string {
    const u = this.displayUser();
    return u ? u.username[0].toUpperCase() : '?';
  }

  /** Map an API post to the Scrawl shape used by ScrawlCardComponent */
  private _mapApiPost(p: ApiPost): Scrawl {
    const displayName = p.is_anonymous
      ? 'Anonymous'
      : (`${p.author.first_name} ${p.author.last_name}`.trim() || p.author.username);
    let avatar: string | undefined;
    if (p.author.avatar) {
      avatar = p.author.avatar.startsWith('http')
        ? p.author.avatar
        : `http://127.0.0.1:8000${p.author.avatar}`;
    }
    return {
      id: String(p.id),
      authorName: displayName,
      authorUsername: p.is_anonymous ? 'anonymous' : p.author.username,
      avatar,
      content: p.content,
      mood: (p.mood as any) || 'none',
      faculty: 'fit',
      createdAt: new Date(p.created_at),
      isAnonymous: p.is_anonymous,
      isSaved: p.is_saved,
      isRescrawled: p.is_rescrawled,
      isLiked: p.is_liked,
      likeCount: p.likes_count,
      saveCount: p.saves_count,
      replyCount: p.replies_count || 0,
      rescrawlCount: p.rescralws_count,
      replies: this.repliesByPost()[String(p.id)] || [],
      showReplyInput: !!this.replyInputOpenByPost()[String(p.id)],
      showReplies: !!this.repliesOpenByPost()[String(p.id)],
      tags: [],
    };
  }


  /** Posts shown in the "My Scrawls" tab — depends on whose profile it is */
  readonly visiblePosts = computed<Scrawl[]>(() =>
    this.isOwnProfile() ? this.localOwnPosts() : this.localOtherPosts()
  );

  // ── Action handlers: own posts ─────────────────────────────────────────────
  onOwnPostAction(event: ScrawlAction): void {
    this.handlePostAction(event);
  }

  onOwnPostToggleReply(id: string): void {
    this.replyInputOpenByPost.update((map) => ({ ...map, [id]: !map[id] }));
    this.refreshAllPostCollections();
  }
  onOwnPostToggleReplies(id: string): void {
    const willOpen = !this.repliesOpenByPost()[id];
    this.repliesOpenByPost.update((map) => ({ ...map, [id]: willOpen }));
    if (willOpen) this.loadReplies(id);
    this.refreshAllPostCollections();
  }
  onOwnPostToggleNestedReply(ev: { scrawlId: string; replyId: string }): void {
    this.repliesByPost.update((map) => ({
      ...map,
      [ev.scrawlId]: this.toggleNestedReplyInput(map[ev.scrawlId] || [], ev.replyId),
    }));
    this.refreshAllPostCollections();
  }
  onOwnPostReplySubmitted(ev: ReplyPayload): void {
    this.submitReply(ev);
  }
  onOwnPostNestedReplySubmitted(ev: NestedReplyPayload): void {
    this.submitNestedReply(ev);
  }
  onOwnPostReplyTriggered(ev: ReplyAction): void {
    this.handleReplyAction(ev);
  }

  // ── Action handlers: feed posts (rescrawls / saved) ───────────────────────
  onFeedPostAction(event: ScrawlAction): void {
    this.handlePostAction(event);
  }
  onFeedPostToggleReply(id: string): void { this.onOwnPostToggleReply(id); }
  onFeedPostToggleReplies(id: string): void { this.onOwnPostToggleReplies(id); }
  onFeedPostToggleNestedReply(ev: { scrawlId: string; replyId: string }): void { this.onOwnPostToggleNestedReply(ev); }
  onFeedPostReplySubmitted(ev: ReplyPayload): void { this.submitReply(ev); }
  onFeedPostNestedReplySubmitted(ev: NestedReplyPayload): void { this.submitNestedReply(ev); }
  onFeedPostReplyTriggered(ev: ReplyAction): void {
    this.handleReplyAction(ev);
  }

  private loadSavedPosts(): void {
    this.postService.getSavedPosts().subscribe({
      next: (posts) => this.savedPostsData.set(posts.map((p) => this._mapApiPost(p))),
      error: (err) => console.error('Failed to load saved posts:', err),
    });
  }

  private loadRescrawledPosts(): void {
    this.postService.getRescrawledPosts().subscribe({
      next: (posts) => this.rescrawledPostsData.set(posts.map((p) => this._mapApiPost(p))),
      error: (err) => console.error('Failed to load rescrawled posts:', err),
    });
  }

  private loadReplies(postId: string): void {
    const numericId = parseInt(postId, 10);
    if (isNaN(numericId)) return;
    this.postService.getReplies(numericId).subscribe({
      next: (replies) => {
        this.repliesByPost.update((map) => ({
          ...map,
          [postId]: replies.map((reply) => this.mapReply(reply)),
        }));
        this.refreshAllPostCollections();
      },
      error: (err) => console.error('Failed to load replies:', err),
    });
  }

  private submitReply(ev: ReplyPayload): void {
    const postId = parseInt(ev.scrawlId, 10);
    if (isNaN(postId)) return;
    this.postService.replyToPost(postId, ev.reply.content).subscribe({
      next: (createdReply) => {
        this.repliesByPost.update((map) => ({
          ...map,
          [ev.scrawlId]: [this.mapReply(createdReply), ...(map[ev.scrawlId] || [])],
        }));
        this.replyInputOpenByPost.update((map) => ({ ...map, [ev.scrawlId]: false }));
        this.incrementReplyCount(ev.scrawlId);
        this.refreshAllPostCollections();
      },
      error: (err) => console.error('Failed to submit reply:', err),
    });
  }

  private handlePostAction(event: ScrawlAction): void {
    const postId = parseInt(event.id, 10);
    if (isNaN(postId)) return;
    if (event.action === 'like') {
      this.postService.likePost(postId).subscribe({
        next: (res) => this.patchPostById(event.id, { isLiked: res.liked, likeCount: res.likes_count }),
        error: (err) => console.error('Failed to toggle like:', err),
      });
      return;
    }
    if (event.action === 'save') {
      this.postService.savePost(postId).subscribe({
        next: (res) => {
          this.patchPostById(event.id, { isSaved: res.saved, saveCount: res.saves_count });
          this.loadSavedPosts();
        },
        error: (err) => console.error('Failed to toggle save:', err),
      });
      return;
    }
    if (event.action === 'rescrawl') {
      this.postService.rescrawlPost(postId).subscribe({
        next: (res) => {
          this.patchPostById(event.id, { isRescrawled: res.rescrawled, rescrawlCount: res.rescralws_count });
          this.loadRescrawledPosts();
        },
        error: (err) => console.error('Failed to toggle rescrawl:', err),
      });
      return;
    }
    if (event.action === 'delete') {
      this.postService.deletePost(postId).subscribe({
        next: () => {
          this.removePostById(event.id);
          this.loadSavedPosts();
          this.loadRescrawledPosts();
        },
        error: (err) => console.error('Failed to delete post:', err),
      });
      return;
    }
    if (event.action === 'edit') {
      const content = (event.payload?.content || '').trim();
      if (!content) return;
      this.postService.updatePost(postId, content).subscribe({
        next: (updated) => this.patchPostById(event.id, this._mapApiPost(updated)),
        error: (err) => console.error('Failed to edit post:', err),
      });
    }
  }

  private patchPostById(id: string, patch: Partial<Scrawl>): void {
    const updater = (posts: Scrawl[]) => posts.map((post) => (post.id === id ? { ...post, ...patch } : post));
    this.localOwnPosts.update(updater);
    this.localOtherPosts.update(updater);
    this.savedPostsData.update(updater);
    this.rescrawledPostsData.update(updater);
  }

  private removePostById(id: string): void {
    const updater = (posts: Scrawl[]) => posts.filter((post) => post.id !== id);
    this.localOwnPosts.update(updater);
    this.localOtherPosts.update(updater);
    this.savedPostsData.update(updater);
    this.rescrawledPostsData.update(updater);
  }

  private incrementReplyCount(id: string): void {
    const updater = (posts: Scrawl[]) =>
      posts.map((post) => (post.id === id ? { ...post, replyCount: post.replyCount + 1 } : post));
    this.localOwnPosts.update(updater);
    this.localOtherPosts.update(updater);
    this.savedPostsData.update(updater);
    this.rescrawledPostsData.update(updater);
  }

  private refreshAllPostCollections(): void {
    const remap = (posts: Scrawl[]) => posts.map((post) => ({ ...post, ...this._mapApiPostToUiState(post.id) }));
    this.localOwnPosts.update(remap);
    this.localOtherPosts.update(remap);
    this.savedPostsData.update(remap);
    this.rescrawledPostsData.update(remap);
  }

  private _mapApiPostToUiState(postId: string): Pick<Scrawl, 'replies' | 'showReplyInput' | 'showReplies'> {
    return {
      replies: this.repliesByPost()[postId] || [],
      showReplyInput: !!this.replyInputOpenByPost()[postId],
      showReplies: !!this.repliesOpenByPost()[postId],
    };
  }

  private mapReply(reply: ApiPost): Scrawl['replies'][number] {
    const displayName = reply.is_anonymous
      ? 'Anonymous'
      : (`${reply.author.first_name} ${reply.author.last_name}`.trim() || reply.author.username);
    let avatar: string | undefined;
    if (reply.author.avatar) {
      avatar = reply.author.avatar.startsWith('http')
        ? reply.author.avatar
        : `http://127.0.0.1:8000${reply.author.avatar}`;
    }
    return {
      id: String(reply.id),
      authorName: displayName,
      authorUsername: reply.is_anonymous ? 'anonymous' : reply.author.username,
      avatar,
      content: reply.content,
      createdAt: new Date(reply.created_at),
      isAnonymous: reply.is_anonymous,
      replies: [],
      showNestedReplyInput: false,
      showNestedReplies: false,
    };
  }

  private submitNestedReply(ev: NestedReplyPayload): void {
    const replyTargetId = parseInt(ev.replyId, 10);
    if (isNaN(replyTargetId)) return;
    this.postService.replyToPost(replyTargetId, ev.reply.content).subscribe({
      next: (createdReply) => {
        this.repliesByPost.update((map) => ({
          ...map,
          [ev.scrawlId]: this.insertChildReply(map[ev.scrawlId] || [], ev.replyId, this.mapReply(createdReply)),
        }));
        this.refreshAllPostCollections();
      },
      error: (err) => console.error('Failed to submit nested reply:', err),
    });
  }

  private toggleNestedReplyInput(replies: Scrawl['replies'], targetReplyId: string): Scrawl['replies'] {
    return replies.map((reply) => {
      if (reply.id === targetReplyId) {
        return { ...reply, showNestedReplyInput: !reply.showNestedReplyInput };
      }
      return { ...reply, replies: this.toggleNestedReplyInput(reply.replies || [], targetReplyId) };
    });
  }

  private insertChildReply(
    replies: Scrawl['replies'],
    parentReplyId: string,
    childReply: Scrawl['replies'][number]
  ): Scrawl['replies'] {
    return replies.map((reply) => {
      if (reply.id === parentReplyId) {
        return {
          ...reply,
          showNestedReplyInput: false,
          replies: [childReply, ...(reply.replies || [])],
        };
      }
      return {
        ...reply,
        replies: this.insertChildReply(reply.replies || [], parentReplyId, childReply),
      };
    });
  }

  // ── Reply actions (edit/delete) ────────────────────────────────────────────
  private handleReplyAction(ev: ReplyAction): void {
    const replyId = parseInt(ev.replyId, 10);
    if (isNaN(replyId)) return;

    if (ev.action === 'delete') {
      this.postService.deletePost(replyId).subscribe({
        next: () => {
          this.removeReplyFromState(ev.scrawlId, ev.replyId);
          this.decrementReplyCount(ev.scrawlId);
        },
        error: (err) => console.error('Failed to delete reply:', err),
      });
    } else if (ev.action === 'edit') {
      const content = (ev.payload || '').trim();
      if (!content) return;
      this.postService.updatePost(replyId, content).subscribe({
        next: (updated) => {
          this.updateReplyInState(ev.scrawlId, ev.replyId, updated.content);
        },
        error: (err) => console.error('Failed to edit reply:', err),
      });
    }
  }

  private removeReplyFromState(scrawlId: string, replyId: string): void {
    this.repliesByPost.update((map) => ({
      ...map,
      [scrawlId]: this.filterReplyRecursive(map[scrawlId] || [], replyId),
    }));
    this.refreshAllPostCollections();
  }

  private filterReplyRecursive(replies: Scrawl['replies'], replyId: string): Scrawl['replies'] {
    return replies.filter(r => r.id !== replyId).map(r => ({
      ...r,
      replies: this.filterReplyRecursive(r.replies || [], replyId),
    }));
  }

  private updateReplyInState(scrawlId: string, replyId: string, newContent: string): void {
    this.repliesByPost.update((map) => ({
      ...map,
      [scrawlId]: this.patchReplyContentRecursive(map[scrawlId] || [], replyId, newContent),
    }));
    this.refreshAllPostCollections();
  }

  private patchReplyContentRecursive(
    replies: Scrawl['replies'],
    replyId: string,
    newContent: string
  ): Scrawl['replies'] {
    return replies.map((r) => {
      if (r.id === replyId) {
        return { ...r, content: newContent };
      }
      return { ...r, replies: this.patchReplyContentRecursive(r.replies || [], replyId, newContent) };
    });
  }

  private decrementReplyCount(id: string): void {
    const updater = (posts: Scrawl[]) =>
      posts.map((post) => (post.id === id ? { ...post, replyCount: Math.max(0, post.replyCount - 1) } : post));
    this.localOwnPosts.update(updater);
    this.localOtherPosts.update(updater);
    this.savedPostsData.update(updater);
    this.rescrawledPostsData.update(updater);
  }

  // ── Mood statistics ───────────────────────────────────────────────────────
  private calculateMoodCount(mood: string): number {
    const posts = this.localOwnPosts();
    // Count posts with the given mood
    let count = posts.filter((p) => p.mood === mood).length;
    
    // Optionally include replies in mood calculation
    const allReplies = Object.values(this.repliesByPost()).flat();
    count += this.countRepliesWithMood(allReplies, mood);
    
    return count;
  }

  private countRepliesWithMood(replies: Scrawl['replies'], mood: string): number {
    let count = 0;
    for (const reply of replies) {
      // Note: replies don't have mood in current model, but if they did:
      // if (reply.mood === mood) count++;
      count += this.countRepliesWithMood(reply.replies || [], mood);
    }
    return count;
  }
}