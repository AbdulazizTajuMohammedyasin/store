from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import KnowledgeArticle
from .services.embeddings import embed_text


@receiver(post_save, sender=KnowledgeArticle)
def update_knowledge_article_embedding(sender, instance, raw, **kwargs):
    if raw:
        return

    embedding = embed_text(f"{instance.title}\n\n{instance.content}")

    # Use an update() query rather than instance.save() so this doesn't
    # re-trigger this same post_save signal.
    KnowledgeArticle.objects.filter(pk=instance.pk).update(embedding=embedding)
